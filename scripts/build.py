#!/usr/bin/env python3
"""Common Ace6 build entry used by local reproduce.sh and Actions.

The caller supplies either legacy CLI flags or Actions-style ACE6_* environment
variables.  Source preparation, optional patch order, configuration, Image
verification, packaging and the build manifest deliberately live here so the
two front ends cannot silently diverge.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import profile as contract  # noqa: E402


class BuildError(contract.Invalid):
    """A build stopped before it could make a success claim."""


FEATURE_PATCHES = {
    "lz4_zstd": ("patches/split/02_lz4.patch", "patches/split/03_zstd.patch"),
    "lz4kd": ("patches/split/04_lz4kd.patch",),
    "baseband_guard": ("patches/split/06_baseband_guard.patch",),
}


def require(condition, message):
    if not condition:
        raise BuildError(message)


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_command(argv, cwd=None, env=None, capture=False, timeout=None):
    command = [str(item) for item in argv]
    result = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        capture_output=capture,
        timeout=timeout,
        check=False,
    )
    if result.returncode:
        detail = ((result.stderr or "") + (result.stdout or ""))[-6000:]
        raise BuildError(f"{command[0]} failed ({result.returncode}): {detail}")
    return result.stdout if capture else ""


def command_output(argv, cwd=None, env=None):
    return run_command(argv, cwd=cwd, env=env, capture=True).strip()


def add_legacy_arguments(parser):
    parser.add_argument("--ksu", choices=("none", "resukisu"), default=argparse.SUPPRESS)
    for flag, dest in (
        ("--susfs", "susfs"), ("--lz4", "lz4_zstd"), ("--lz4kd", "lz4kd"),
        ("--show-all-algos", "show_all_algos"), ("--zram-writeback", "zram_writeback"),
        ("--bbg", "baseband_guard"), ("--cve", "cve_patch"),
        ("--better-net", "better_net"), ("--bbr", "bbr"), ("--kpm", "kpm"),
        ("--rekernel", "rekernel"), ("--no-attribution", "no_attribution"),
    ):
        parser.add_argument(flag, dest=dest, action="store_true", default=argparse.SUPPRESS)
    for flag, dest in (
        ("--droidspaces", "droidspaces"), ("--suffix", "kernel_suffix"),
        ("--user", "build_user"), ("--host", "build_host"), ("--time", "build_time"),
    ):
        parser.add_argument(flag, dest=dest, default=argparse.SUPPRESS)


def make_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", action="store_true", help="read canonical inputs from ACE6_* environment variables")
    parser.add_argument("--inputs", type=Path, help="flat or normalized JSON input")
    parser.add_argument("--profile", help="explicit profile name")
    parser.add_argument("--fingerprint", action="store_true", help="resolve IDs for cache keys without downloading")
    parser.add_argument("--verify-toolchain", type=Path, metavar="ARCHIVE", help="verify a locked toolchain archive")
    parser.add_argument("--dry-run", action="store_true", help="validate and print the build plan without source changes")
    parser.add_argument("--work", type=Path, help="fresh isolated build workspace")
    parser.add_argument("--out", type=Path, help="artifact directory")
    parser.add_argument("--repo-base", help="optional GitHub mirror/prefix for locked source fetches")
    parser.add_argument("--kernel-src", type=Path, help="clean exact-commit kernel source provider")
    parser.add_argument("--source", action="append", default=[], metavar="NAME=PATH", help="clean exact-commit source provider")
    parser.add_argument("--clean", action="store_true", help="remove only the selected work directory before building")
    parser.add_argument("--jobs", type=int, help="parallel make jobs")
    add_legacy_arguments(parser)
    return parser


def strict_bool(value, field):
    require(value in ("true", "false"), f"{field} must be exactly true or false")
    return value == "true"


def workflow_input():
    fields = contract.read_json(ROOT / "schemas/input-fields.json")
    raw = {}
    for field, spec in fields.items():
        key = "ACE6_" + field.upper()
        if key not in os.environ:
            continue
        value = os.environ[key]
        raw[field] = strict_bool(value, field) if spec["type"] == "boolean" else value
    return raw


def legacy_input(args):
    tokens = []
    for dest, flag in (
        ("ksu", "--ksu"), ("droidspaces", "--droidspaces"),
        ("kernel_suffix", "--suffix"), ("build_user", "--user"),
        ("build_host", "--host"), ("build_time", "--time"),
    ):
        if hasattr(args, dest):
            tokens.extend((flag, getattr(args, dest)))
    for dest, flag in (
        ("susfs", "--susfs"), ("lz4_zstd", "--lz4"), ("lz4kd", "--lz4kd"),
        ("show_all_algos", "--show-all-algos"), ("zram_writeback", "--zram-writeback"),
        ("baseband_guard", "--bbg"), ("cve_patch", "--cve"),
        ("better_net", "--better-net"), ("bbr", "--bbr"), ("kpm", "--kpm"),
        ("rekernel", "--rekernel"),
    ):
        if hasattr(args, dest):
            tokens.append(flag)
    if hasattr(args, "no_attribution"):
        tokens.append("--no-attribution")
    return contract.legacy_arguments(tokens)


def resolve_inputs(args):
    require(not (args.workflow and args.inputs), "--workflow and --inputs are mutually exclusive")
    if args.workflow:
        raw = workflow_input()
    elif args.inputs:
        raw = contract.read_json(args.inputs)
    else:
        raw = legacy_input(args)
    return contract.normalize(raw, args.profile)


def parse_sources(items, lock, kernel_src=None):
    external = {}
    for item in items:
        name, separator, value = item.partition("=")
        require(separator and name in lock["sources"] and value and name not in external,
                f"invalid or duplicate --source: {item}")
        external[name] = str(Path(value).expanduser().resolve())
    if kernel_src:
        require("kernel" not in external, "--kernel-src conflicts with --source kernel")
        external["kernel"] = str(kernel_src.expanduser().resolve())
    if os.environ.get("KERNEL_SRC"):
        require("kernel" not in external, "KERNEL_SRC conflicts with an explicit kernel source")
        external["kernel"] = str(Path(os.environ["KERNEL_SRC"]).expanduser().resolve())
    root = os.environ.get("ACE6_SOURCE_ROOT")
    if root:
        source_root = Path(root).expanduser().resolve()
        for name, source in lock["sources"].items():
            if name in external:
                continue
            candidates = (source_root / name, source_root / source["directory"])
            for candidate in candidates:
                if candidate.is_dir():
                    external[name] = str(candidate)
                    break
    for name in lock["sources"]:
        key = "ACE6_SOURCE_" + name.upper()
        if os.environ.get(key):
            require(name not in external, f"{key} conflicts with another source provider")
            external[name] = str(Path(os.environ[key]).expanduser().resolve())
    return external


def source_url_overrides(lock, repo_base):
    if not repo_base or repo_base.rstrip("/") in ("https://github.com", "http://github.com"):
        return {}
    prefix = repo_base.rstrip("/")
    result = {}
    for name, source in lock["sources"].items():
        url = source["url"]
        if url.startswith("https://github.com/"):
            result[name] = prefix + "/" + url
    return result


def safe_component(value):
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    return value.strip("._-") or "value"


def kernel_localversion(config, lock):
    suffix = config["identity"]["kernel_suffix"] or ("g" + lock["sources"]["kernel"]["commit"][:12])
    return "-4k-" + suffix


def source_patch_record(path, operation="patch", **extra):
    record = {"path": str(path.relative_to(ROOT)), "sha256": hash_file(path), "operation": operation}
    record.update(extra)
    return record


def validate_feature_lock(config):
    lock_path = ROOT / "manifests/build-features.json"
    lock = contract.read_json(lock_path)
    selected = {}
    for feature, group in FEATURE_PATCHES.items():
        if not config["features"][feature]:
            continue
        name = feature
        entry = lock["groups"].get(name)
        require(entry, f"feature lock is missing group: {name}")
        files = entry["files"]
        digest = hashlib.sha256()
        for item in sorted(files, key=lambda value: value["path"]):
            path = ROOT / item["path"]
            require(path.is_file() and hash_file(path) == item["sha256"],
                    f"feature lock hash mismatch: {item['path']}")
            digest.update(item["path"].encode())
            digest.update(bytes.fromhex(item["sha256"]))
        require(digest.hexdigest() == entry["tree_sha256"], f"feature lock tree mismatch: {name}")
        selected[name] = entry
    return selected


def apply_optional_patch(kernel, relative, records):
    patch_path = ROOT / relative
    require(patch_path.is_file(), f"missing locked feature patch: {relative}")
    before = len(records)
    command = ["patch", "-p1", "-F3", "--batch", "-f"]
    with patch_path.open("rb") as stream:
        result = subprocess.run(command, cwd=kernel, stdin=stream, text=False, capture_output=True, check=False)
    detail = (result.stdout + result.stderr).decode(errors="replace")[-6000:]
    require(result.returncode == 0, f"feature patch failed: {relative}\n{detail}")
    records.append(source_patch_record(patch_path, fuzz="fuzz" in detail.lower(), log_tail=detail))
    assert len(records) == before + 1


def copy_file(source, target):
    display = str(source)
    try:
        display = str(source.relative_to(ROOT))
    except ValueError:
        pass
    require(source.is_file(), f"missing source: {display}")
    require(not target.is_symlink(), f"refusing to overwrite symlink: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def copy_tree(source, target):
    require(source.is_dir() and not source.is_symlink(), f"missing extra directory: {source}")
    require(not target.is_symlink(), f"refusing to overwrite symlink directory: {target}")
    for item in sorted(source.rglob("*")):
        relative = item.relative_to(source)
        destination = target / relative
        if item.is_dir():
            require(not destination.is_symlink(), f"refusing to traverse symlink: {destination}")
            destination.mkdir(parents=True, exist_ok=True)
        else:
            copy_file(item, destination)


def copy_feature_extras(kernel, features, records):
    def record_tree(relative, target):
        source = ROOT / relative
        copy_tree(source, kernel / target)
        for item in sorted(source.rglob("*")):
            if item.is_file():
                records.append(source_patch_record(item, operation="copy", destination=str((Path(target) / item.relative_to(source)))))

    if features["lz4_zstd"]:
        record_tree("patches/extra/lib/lz4", "lib/lz4")
        for relative, target in (
            ("patches/extra/lib/zstd/common/allocations.h", "lib/zstd/common/allocations.h"),
            ("patches/extra/lib/zstd/common/bits.h", "lib/zstd/common/bits.h"),
            ("patches/extra/lib/zstd/compress/zstd_preSplit.c", "lib/zstd/compress/zstd_preSplit.c"),
            ("patches/extra/lib/zstd/compress/zstd_preSplit.h", "lib/zstd/compress/zstd_preSplit.h"),
        ):
            source = ROOT / relative
            copy_file(source, kernel / target)
            records.append(source_patch_record(source, operation="copy", destination=target))
    if features["lz4kd"]:
        for relative, target in (
            ("patches/extra/crypto/lz4k.c", "crypto/lz4k.c"),
            ("patches/extra/crypto/lz4kd.c", "crypto/lz4kd.c"),
            ("patches/extra/include/linux/lz4k.h", "include/linux/lz4k.h"),
            ("patches/extra/include/linux/lz4kd.h", "include/linux/lz4kd.h"),
        ):
            source = ROOT / relative
            copy_file(source, kernel / target)
            records.append(source_patch_record(source, operation="copy", destination=target))
        record_tree("patches/extra/lib/lz4k", "lib/lz4k")
        record_tree("patches/extra/lib/lz4kd", "lib/lz4kd")
    if features["baseband_guard"]:
        record_tree("patches/extra/Baseband-guard", "Baseband-guard")
        link = kernel / "security/baseband-guard"
        if link.exists() or link.is_symlink():
            require(link.is_symlink(), f"refusing to replace existing directory: {link}")
            link.unlink()
        link.symlink_to("../Baseband-guard")


def set_config(kernel, *operations):
    run_command([kernel / "scripts/config", "--file", kernel / ".config", *operations], cwd=kernel, capture=True)


def read_config(path: Path, symbol: str):
    text = path.read_text(errors="replace")
    match = re.search(rf"^CONFIG_{re.escape(symbol)}=(.*)$", text, re.MULTILINE)
    if match:
        return match.group(1)
    if re.search(rf"^# CONFIG_{re.escape(symbol)} is not set$", text, re.MULTILINE):
        return "n"
    return None


def require_config(path: Path, symbol: str, expected="y"):
    actual = read_config(path, symbol)
    if expected == "n":
        require(actual != "y", f"CONFIG_{symbol} expected disabled, found {actual}")
    else:
        require(actual == expected, f"CONFIG_{symbol} expected {expected}, found {actual}")


def configure_kernel(kernel, config, lock):
    config_path = kernel / ".config"
    copy_file(ROOT / "config/config_ace6_final.config", config_path)
    features = config["features"]
    identity = config["identity"]
    if features["droidspaces"] == "standard":
        merge = kernel / "scripts/kconfig/merge_config.sh"
        fragment = ROOT / "config/config_droidspaces_standard_6.6.fragment"
        run_command(["bash", merge, "-m", config_path, fragment], cwd=kernel, capture=True)

    set_config(kernel, "--set-str", "CONFIG_LOCALVERSION", kernel_localversion(config, lock), "-d", "CONFIG_LOCALVERSION_AUTO")
    if features["ksu_type"] == "none":
        set_config(kernel, "-d", "CONFIG_KSU", "-d", "CONFIG_KSU_SUSFS")
    else:
        set_config(kernel, "-e", "CONFIG_KSU")
        if features["susfs"]:
            set_config(kernel, "-e", "CONFIG_KSU_SUSFS")
        else:
            set_config(kernel, "-d", "CONFIG_KSU_SUSFS")
    if features["droidspaces"] == "false":
        set_config(kernel, "-d", "CONFIG_SYSVIPC", "-d", "CONFIG_NTSYNC", "-d", "CONFIG_DRM_LINDROID_EVDI")
    elif features["droidspaces"] != "extend":
        set_config(kernel, "-d", "CONFIG_DRM_LINDROID_EVDI")
    if features["lz4_zstd"]:
        set_config(kernel, "-e", "CONFIG_CRYPTO_LZ4", "-e", "CONFIG_CRYPTO_ZSTD")
    if features["lz4kd"]:
        set_config(
            kernel, "-d", "CONFIG_ZRAM_DEF_COMP_LZO", "-d", "CONFIG_ZRAM_DEF_COMP_LZORLE",
            "-d", "CONFIG_ZRAM_DEF_COMP_LZ4", "-d", "CONFIG_ZRAM_DEF_COMP_LZ4HC",
            "-d", "CONFIG_ZRAM_DEF_COMP_LZ4K", "-d", "CONFIG_ZRAM_DEF_COMP_LZ4KD",
            "-d", "CONFIG_ZRAM_DEF_COMP_DEFLATE", "-d", "CONFIG_ZRAM_DEF_COMP_842",
            "-d", "CONFIG_ZRAM_DEF_COMP_ZSTD", "-e", "CONFIG_CRYPTO_LZ4K",
            "-e", "CONFIG_CRYPTO_LZ4KD", "-e", "CONFIG_LZ4K_COMPRESS",
            "-e", "CONFIG_LZ4K_DECOMPRESS", "-e", "CONFIG_LZ4KD_COMPRESS",
            "-e", "CONFIG_LZ4KD_DECOMPRESS", "-e", "CONFIG_ZRAM_DEF_COMP_LZ4KD",
        )
    else:
        set_config(
            kernel, "-d", "CONFIG_LZ4K_COMPRESS", "-d", "CONFIG_LZ4K_DECOMPRESS",
            "-d", "CONFIG_LZ4KD_COMPRESS", "-d", "CONFIG_LZ4KD_DECOMPRESS",
            "-d", "CONFIG_CRYPTO_LZ4K", "-d", "CONFIG_CRYPTO_LZ4KD",
            "-d", "CONFIG_ZRAM_DEF_COMP_LZO", "-d", "CONFIG_ZRAM_DEF_COMP_LZORLE",
            "-d", "CONFIG_ZRAM_DEF_COMP_LZ4", "-d", "CONFIG_ZRAM_DEF_COMP_LZ4HC",
            "-d", "CONFIG_ZRAM_DEF_COMP_LZ4K", "-d", "CONFIG_ZRAM_DEF_COMP_LZ4KD",
            "-d", "CONFIG_ZRAM_DEF_COMP_DEFLATE", "-d", "CONFIG_ZRAM_DEF_COMP_842",
            "-d", "CONFIG_ZRAM_DEF_COMP_ZSTD", "-e", "CONFIG_CRYPTO_LZO",
            "-e", "CONFIG_ZRAM_DEF_COMP_LZORLE",
        )
    if features["show_all_algos"]:
        set_config(kernel, "-e", "CONFIG_CRYPTO_LZO", "-e", "CONFIG_CRYPTO_LZ4", "-e", "CONFIG_CRYPTO_ZSTD",
                   "-e", "CONFIG_CRYPTO_DEFLATE", "-e", "CONFIG_CRYPTO_LZ4HC", "-e", "CONFIG_CRYPTO_842")
    else:
        set_config(kernel, "-d", "CONFIG_CRYPTO_LZ4HC", "-d", "CONFIG_CRYPTO_842")
    if features["zram_writeback"]:
        set_config(kernel, "-e", "CONFIG_ZRAM_WRITEBACK")
    else:
        set_config(kernel, "-d", "CONFIG_ZRAM_WRITEBACK", "-d", "CONFIG_ZRAM_MEMORY_TRACKING",
                   "-d", "CONFIG_ZRAM_TRACK_ENTRY_ACTIME")
    if features["baseband_guard"]:
        set_config(kernel, "-e", "CONFIG_BBG")
    else:
        set_config(kernel, "-d", "CONFIG_BBG")
    if features["better_net"]:
        set_config(kernel, "-e", "CONFIG_IP_SET", "-e", "CONFIG_BPF_STREAM_PARSER", "-e", "CONFIG_IP6_NF_NAT")
    else:
        set_config(kernel, "-d", "CONFIG_IP_SET", "-d", "CONFIG_BPF_STREAM_PARSER", "-d", "CONFIG_IP6_NF_NAT")
    if features["bbr"]:
        set_config(kernel, "-e", "CONFIG_TCP_CONG_ADVANCED", "-e", "CONFIG_TCP_CONG_BBR", "-d", "CONFIG_DEFAULT_BBR")
    else:
        set_config(kernel, "-d", "CONFIG_TCP_CONG_BBR", "-d", "CONFIG_DEFAULT_BBR")
    if features["rekernel"]:
        set_config(kernel, "-e", "CONFIG_REKERNEL")
    else:
        set_config(kernel, "-d", "CONFIG_REKERNEL")
    run_command(["make", "LLVM=1", "LLVM_IAS=1", "ARCH=arm64", "olddefconfig"], cwd=kernel, capture=True,
                env={**os.environ, "LLVM": "1", "LLVM_IAS": "1"})
    expected = '"lz4kd"' if features["lz4kd"] else '"lzo-rle"'
    require(read_config(config_path, "ZRAM_DEF_COMP") == expected, "default zram compressor contract failed")
    require_config(config_path, "KSU", "y" if features["ksu_type"] != "none" else "n")
    require_config(config_path, "KSU_SUSFS", "y" if features["susfs"] else "n")
    require_config(config_path, "REKERNEL", "y" if features["rekernel"] else "n")
    if features["droidspaces"] == "extend":
        for symbol in ("SYSVIPC", "NTSYNC", "DRM_LINDROID_EVDI"):
            require_config(config_path, symbol)
    elif features["droidspaces"] == "standard":
        for symbol in ("SYSVIPC", "NTSYNC"):
            require_config(config_path, symbol)
        require_config(config_path, "DRM_LINDROID_EVDI", "n")
    else:
        for symbol in ("SYSVIPC", "NTSYNC", "DRM_LINDROID_EVDI"):
            require_config(config_path, symbol, "n")
    require_config(config_path, "ZRAM_WRITEBACK", "y" if features["zram_writeback"] else "n")
    require_config(config_path, "BBG", "y" if features["baseband_guard"] else "n")
    for symbol in ("IP_SET", "BPF_STREAM_PARSER", "IP6_NF_NAT"):
        require_config(config_path, symbol, "y" if features["better_net"] else "n")
    require_config(config_path, "TCP_CONG_BBR", "y" if features["bbr"] else "n")
    if features["show_all_algos"]:
        for symbol in ("CRYPTO_LZO", "CRYPTO_LZ4", "CRYPTO_ZSTD", "CRYPTO_DEFLATE",
                       "CRYPTO_LZ4HC", "CRYPTO_842"):
            require_config(config_path, symbol)
    if features["lz4kd"]:
        for symbol in ("CRYPTO_LZ4K", "CRYPTO_LZ4KD", "LZ4K_COMPRESS", "LZ4K_DECOMPRESS",
                       "LZ4KD_COMPRESS", "LZ4KD_DECOMPRESS"):
            require_config(config_path, symbol)
    if not features["bbr"]:
        require(read_config(config_path, "TCP_CONG_BBR") != "y", "BBR remained enabled while disabled")
    if not features["better_net"]:
        for symbol in ("IP_SET", "BPF_STREAM_PARSER", "IP6_NF_NAT"):
            require(read_config(config_path, symbol) != "y", f"{symbol} remained enabled while disabled")
    if not features["zram_writeback"]:
        for symbol in ("ZRAM_WRITEBACK", "ZRAM_MEMORY_TRACKING", "ZRAM_TRACK_ENTRY_ACTIME"):
            require(read_config(config_path, symbol) != "y", f"{symbol} remained enabled while disabled")
    return {"sha256": hash_file(config_path), "default_compressor": expected.strip('"')}


def toolchain_info(lock):
    clang = shutil.which("clang") or ""
    lld = shutil.which("ld.lld") or ""
    require(clang and lld, "clang and ld.lld are required for the locked build")
    version = command_output([clang, "--version"]).splitlines()[0]
    require(re.search(r"clang version 21\.", version) is not None,
            f"clang does not match locked AOSP Clang 21: {version}")
    return {"clang": version, "linker": "ld.lld", "locked": lock["resources"]["clang"]["version"]}


def verify_image(kernel):
    image = kernel / "arch/arm64/boot/Image"
    require(image.is_file() and image.stat().st_size > 0, "kernel Image is missing or empty")
    release_path = kernel / "include/config/kernel.release"
    require(release_path.is_file(), "include/config/kernel.release is missing")
    release = release_path.read_text().strip()
    require(release, "kernel.release is empty")
    strings = command_output(["strings", image])
    matches = re.findall(r"Linux version ([^\s\x00]+)", strings)
    require(matches, "no Linux version banner found in Image")
    banner_release = matches[0]
    require(banner_release == release, f"Image release mismatch: expected {release}, found {banner_release}")
    version = ""
    uts = kernel / "include/generated/utsversion.h"
    if uts.is_file():
        text = uts.read_text(errors="replace")
        match = re.search(r'#define UTS_VERSION\s+"([^"]+)"', text)
        version = match.group(1) if match else ""
    return {"path": "arch/arm64/boot/Image", "sha256": hash_file(image), "size": image.stat().st_size,
            "release": release, "banner_release": banner_release, "uts_version": version}


def package_independent_modules(work, out):
    """Package only runtime files for the self-authored KSU modules.

    These zips are deliberately separate from AK3.  Build sources and npm
    metadata are not runtime module files and are excluded from the package.
    """
    require(shutil.which("zip"), "zip is required for independent module packaging")
    source_root = ROOT / "modules"
    pack_root = work / "module-pack"
    require(source_root.is_dir(), "self-authored module directory is missing")
    require(not pack_root.exists(), "module-pack directory unexpectedly exists in fresh workspace")
    pack_root.mkdir()
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
    artifacts = []
    for source in sorted(source_root.iterdir()):
        if not source.is_dir():
            continue
        for item in source.rglob("*"):
            require(not item.is_symlink(), f"refusing symlink in module source: {item}")
        prop = source / "module.prop"
        require(prop.is_file(), f"module source lacks module.prop: {source.name}")
        metadata = {}
        for line in prop.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator and key in ("id", "version"):
                metadata[key] = value
        module_id = metadata.get("id", "")
        version = metadata.get("version", "")
        require(re.fullmatch(r"[A-Za-z0-9._-]+", module_id) is not None,
                f"invalid KSU module id: {module_id!r}")
        require(version and "\n" not in version and "\r" not in version,
                f"invalid KSU module version: {module_id}")
        destination = pack_root / module_id
        shutil.copytree(source, destination, ignore=shutil.ignore_patterns("webui-src"))
        require(not any("node_modules" in item.parts for item in destination.rglob("*")),
                f"build dependency leaked into KSU module package: {module_id}")
        version_component = version[1:] if version.startswith("v") else version
        zip_name = f"Kernel-Ace6-module-{safe_component(module_id)}-v{safe_component(version_component)}-{stamp}.zip"
        zip_path = out / zip_name
        require(not zip_path.exists(), f"artifact already exists: {zip_path}")
        run_command(["zip", "-r9", zip_path, ".", "-x", "*.git*"], cwd=destination, capture=True)
        artifacts.append({
            "kind": "ksu-module", "module_id": module_id, "path": zip_name,
            "sha256": hash_file(zip_path), "size": zip_path.stat().st_size,
            "runtime_root": module_id,
        })
    require(artifacts, "no self-authored KSU modules found")
    return artifacts


def prepare_package(kernel, config, lock, work, out, image_record):
    out.mkdir(parents=True, exist_ok=True)
    mode = config["artifacts"]["artifact_mode"]
    require(mode not in ("boot", "all"),
            "boot.img/all packaging is blocked: a target boot image with ramdisk, DTB and AVB inputs is required (T18)")
    artifacts = []
    zip_name = ""
    if mode in ("ak3", "all"):
        require(shutil.which("zip"), "zip is required for AK3 packaging")
        pack = work / "pack"
        require(not pack.exists(), "pack directory unexpectedly exists in fresh workspace")
        shutil.copytree(ROOT / "ak3", pack)
        copy_file(kernel / "arch/arm64/boot/Image", pack / "Image")
        script = pack / "anykernel.sh"
        text = script.read_text()
        display = config["identity"]["build_user"] if config["identity"]["attribution_enable"] else "Ace6 Kernel"
        replacement = "kernel.string=Ace6 Kernel | Build by " + display if config["identity"]["attribution_enable"] else "kernel.string=Ace6 Kernel"
        text, count = re.subn(r"^kernel\.string=.*$", lambda _match: replacement, text, count=1, flags=re.MULTILINE)
        require(count == 1, "AK3 kernel.string entry is missing")
        script.write_text(text)
        identity = config["identity"]
        user = safe_component(identity["build_user"]) if identity["attribution_enable"] else "Ace6"
        suffix_part = "-" + safe_component(identity["kernel_suffix"]) if identity["kernel_suffix"] else ""
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
        ksu = lock["resources"].get("ksu_identity") or {}
        suffix = f"-ksu{ksu['version_code']}" if config["features"]["ksu_type"] != "none" else ""
        zip_name = f"Kernel-Ace6-{user}{suffix_part}{suffix}-{stamp}.zip"
        zip_path = out / zip_name
        require(not zip_path.exists(), f"artifact already exists: {zip_path}")
        run_command(["zip", "-r9", zip_path, ".", "-x", "*.git*"], cwd=pack, capture=True)
        artifacts.append({"kind": "ak3", "path": zip_name, "sha256": hash_file(zip_path), "size": zip_path.stat().st_size})
    if mode in ("image", "all"):
        image_path = out / "Image"
        require(not image_path.exists(), f"artifact already exists: {image_path}")
        copy_file(kernel / "arch/arm64/boot/Image", image_path)
        artifacts.append({"kind": "Image", "path": "Image", "sha256": hash_file(image_path), "size": image_path.stat().st_size})
    if config["artifacts"]["independent_modules"]:
        artifacts.extend(package_independent_modules(work, out))
    primary = zip_name or (artifacts[0]["path"] if artifacts else "")
    require(primary, "artifact selection produced no output")
    return primary, artifacts


def emit_output(name, value):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as stream:
            stream.write(f"{name}={value}\n")


def emit_env(name, value):
    path = os.environ.get("GITHUB_ENV")
    if path:
        with open(path, "a", encoding="utf-8") as stream:
            stream.write(f"{name}={value}\n")


def resolve(args):
    config, selected = resolve_inputs(args)
    lock = contract.read_json(ROOT / "manifests/locks" / (selected["name"] + ".lock.json"))
    contract.validate_lock(lock, config, selected)
    validate_feature_lock(config)
    report = contract.preflight(config, selected, lock, phase="build")
    require(report["prepare_allowed"], "build blocked: " + "; ".join(report["blockers"]))
    if config["features"]["kpm"]:
        require(lock["resources"].get("kpm"), "KPM is not pinned for this profile; stop before build (T17)")
    return config, selected, lock, report


def fingerprint(args):
    config, selected, lock, _ = resolve(args)
    payload = {
        "config_id": contract.digest(config), "lock_id": contract.digest(lock),
        "kernel_commit": lock["sources"]["kernel"]["commit"],
        "toolchain_sha256": lock["resources"]["clang"]["sha256"],
    }
    payload["fingerprint"] = contract.digest(payload)
    emit_env("SRC_COMMIT", payload["kernel_commit"])
    emit_env("ACE6_CONFIG_ID", payload["config_id"])
    emit_env("ACE6_LOCK_ID", payload["lock_id"])
    emit_env("CCACHE_FP", payload["fingerprint"])
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def verify_toolchain(args):
    _, _, lock, _ = resolve(args)
    archive = args.verify_toolchain.expanduser().resolve()
    require(archive.is_file(), f"toolchain archive is missing: {archive}")
    actual = hash_file(archive)
    expected = lock["resources"]["clang"]["sha256"]
    require(actual == expected, f"toolchain hash mismatch: expected {expected}, found {actual}")
    print(f"toolchain sha256 verified: {actual}")


def dry_run(args):
    config, selected, lock, report = resolve(args)
    feature_lock = validate_feature_lock(config)
    identity = config["identity"]
    optional = []
    for feature, paths in FEATURE_PATCHES.items():
        if config["features"][feature]:
            optional.extend(source_patch_record(ROOT / path) for path in paths)
    result = {
        "profile": selected["name"], "config_id": contract.digest(config), "lock_id": contract.digest(lock),
        "sources": {name: {"commit": value["commit"], "url": value["url"]} for name, value in lock["sources"].items()},
        "optional_patches": optional, "localversion": "-4k-" + (config["identity"]["kernel_suffix"] or "g" + lock["sources"]["kernel"]["commit"][:12]),
        "feature_lock_id": contract.digest(feature_lock),
        "default_compressor": "lz4kd" if config["features"]["lz4kd"] else "lzo-rle",
        "identity": {
            "display": identity,
            "filename": {
                "user": safe_component(identity["build_user"]) if identity["attribution_enable"] else "Ace6",
                "suffix": safe_component(identity["kernel_suffix"]) if identity["kernel_suffix"] else "",
            },
        },
        "build_preflight": report, "work": str(args.work), "out": str(args.out),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))


def safe_clean(path, forbidden):
    path = path.expanduser().resolve()
    require(path not in forbidden and path.parent != Path("/") and path.name not in
            ("home", "git", "workspace", "ace6", "tmp"), f"refusing broad clean target: {path}")
    require(not ROOT.is_relative_to(path), f"refusing to clean a parent of the repository: {path}")
    if path.is_symlink():
        raise BuildError(f"refusing to clean symlink: {path}")
    if path.exists():
        require(path.is_dir(), f"clean target is not a directory: {path}")
        shutil.rmtree(path)


def build_path(value, default):
    path = Path(value) if value else Path(default)
    return path.expanduser() if path.is_absolute() else (ROOT / path).resolve()


def build(args):
    config, selected, lock, report = resolve(args)
    feature_lock = validate_feature_lock(config)
    work = build_path(args.work or os.environ.get("ACE6_WORK", os.environ.get("WORK_DIR")), ROOT / "work")
    out = build_path(args.out or os.environ.get("ACE6_OUT", os.environ.get("OUT_DIR")), ROOT / "out")
    if args.clean:
        safe_clean(work, {ROOT, Path("/")})
    require(not work.exists() and not work.is_symlink(), f"work directory already exists: {work}; choose a fresh path or --clean")
    external = parse_sources(args.source, lock, args.kernel_src)
    work.parent.mkdir(parents=True, exist_ok=True)
    print(f"profile={selected['name']} config={contract.digest(config)} lock={contract.digest(lock)}")
    print(f"preparing exact sources in {work}")
    source_manifest = contract.prepare(
        config, selected, lock, work, external=external, root=ROOT, phase="build",
        source_urls=source_url_overrides(
            lock, args.repo_base or os.environ.get("ACE6_REPO_BASE") or os.environ.get("REPO_BASE")
        ),
    )
    kernel = work / lock["sources"]["kernel"]["directory"]
    records = list(source_manifest["steps"])
    features = config["features"]
    for feature in ("lz4_zstd", "lz4kd", "baseband_guard"):
        if features[feature]:
            for path in FEATURE_PATCHES[feature]:
                apply_optional_patch(kernel, path, records)
    copy_feature_extras(kernel, features, records)
    if config["features"]["cve_patch"]:
        print("cve_patch=true: upstream lineage-23.2 already carries the documented fixes; no extra patch")
    if features["ksu_type"] != "none":
        kbuild = kernel / "KernelSU/kernel/Kbuild"
        if kbuild.is_file():
            text = kbuild.read_text()
            name = config["identity"]["build_user"] if config["identity"]["attribution_enable"] else ""
            text, count = re.subn(
                r"^REPO_NAME := .*$", lambda _match: "REPO_NAME := " + name,
                text, count=1, flags=re.MULTILINE,
            )
            require(count == 1, "KernelSU REPO_NAME entry is missing")
            kbuild.write_text(text)
    config_record = configure_kernel(kernel, config, lock)
    toolchain = toolchain_info(lock)
    build_status = "skipped"
    image_record = None
    build_started = dt.datetime.now(dt.timezone.utc).isoformat()
    if config["artifacts"]["debug_skip_build"]:
        image = kernel / "arch/arm64/boot/Image"
        require(not image.exists(), "debug skip refuses to reuse an existing Image")
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(b"DEBUG DUMMY IMAGE\n")
        print("debug_skip_build=true: created a dummy Image; no compiled-kernel claim")
    else:
        env = os.environ.copy()
        env.update({"LLVM": "1", "LLVM_IAS": "1", "ARCH": "arm64"})
        identity = config["identity"]
        env["KBUILD_BUILD_USER"] = identity["build_user"] if identity["attribution_enable"] else ""
        env["KBUILD_BUILD_HOST"] = identity["build_host"] if identity["attribution_enable"] else ""
        if identity["build_time"] and identity["build_time"].lower() != "n":
            env["KBUILD_BUILD_TIMESTAMP"] = identity["build_time"]
        jobs = args.jobs or int(os.environ.get("ACE6_JOBS", os.cpu_count() or 1))
        make = ["make", "LLVM=1", "LLVM_IAS=1", "ARCH=arm64", f"-j{jobs}", "Image"]
        if "CC" not in env and config["artifacts"]["ccache_enable"] and shutil.which("ccache"):
            env["CC"] = "ccache clang"
        if "LD" not in env and shutil.which("ld.lld"):
            env["LD"] = "ld.lld"
        if config["artifacts"]["ccache_debug"]:
            debug_dir = work / "_tmp"
            debug_dir.mkdir(parents=True, exist_ok=True)
            env.setdefault("CCACHE_LOGFILE", str(debug_dir / "ccache.log"))
        print(f"building Image with {jobs} jobs")
        run_command(make, cwd=kernel, env=env)
        build_status = "built"
    image_record = verify_image(kernel) if build_status == "built" else {
        "path": "arch/arm64/boot/Image", "sha256": hash_file(kernel / "arch/arm64/boot/Image"),
        "size": (kernel / "arch/arm64/boot/Image").stat().st_size, "debug_dummy": True,
    }
    artifact_name, artifacts = prepare_package(kernel, config, lock, work, out, image_record)
    ak3_name = next((item["path"] for item in artifacts if item["kind"] == "ak3"), "")
    final_sources = {}
    for name, source in lock["sources"].items():
        destination = work / source["directory"]
        run_command(["git", "-C", destination, "add", "-A"])
        final_sources[name] = {
            "commit": source["commit"], "tree": source_manifest["sources"][name]["tree"],
            "prepared_tree": command_output(["git", "-C", destination, "write-tree"]),
        }
    identity = config["identity"]
    localversion = kernel_localversion(config, lock)
    filename_user = safe_component(identity["build_user"]) if identity["attribution_enable"] else "Ace6"
    filename_suffix = safe_component(identity["kernel_suffix"]) if identity["kernel_suffix"] else ""
    ksu_identity = lock["resources"].get("ksu_identity") or {}
    ksu_marker = f"ksu{ksu_identity['version_code']}" if features["ksu_type"] != "none" else ""
    resolved_build_time = identity["build_time"] if identity["build_time"] and identity["build_time"].lower() != "n" else build_started
    manifest = {
        "schema_version": 1, "manifest_type": "build", "phase": "debug-skipped" if build_status == "skipped" else "built",
        "config": config, "config_id": contract.digest(config), "profile": selected["name"],
        "profile_id": contract.digest(selected), "lock_id": contract.digest(lock),
        "source_manifest_id": source_manifest["manifest_id"], "sources": final_sources,
        "feature_lock_id": contract.digest(feature_lock), "feature_sources": feature_lock,
        "steps": records, "toolchain": toolchain, "final_config": config_record,
        "build": {"status": build_status, "started_utc": build_started, "kernel_release": image_record.get("release"),
                   "image": image_record},
        "artifacts": artifacts, "runtime": "not-tested", "preflight": report,
        "publication": {
            "requested": bool(config["artifacts"]["release_enable"]),
            "allowed": bool(report["release_allowed"]),
            "published": False,
            "reason": "local build records release intent; publication requires runtime, rollback and handoff gates",
        },
        "reproducibility": {"source_preparation": True, "byte_identical_build": False},
        "resolved": {
            "build_date_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"),
            "build_time": resolved_build_time,
            "kernel_commit": lock["sources"]["kernel"]["commit"],
            "kernel_localversion": localversion,
            "artifact_name": artifact_name,
            "identity": {
                "display": {
                    "user": identity["build_user"], "host": identity["build_host"],
                    "suffix": identity["kernel_suffix"], "tag": identity["tag"],
                    "attribution": identity["attribution_enable"],
                },
                "filename": {"user": filename_user, "suffix": filename_suffix, "ksu_marker": ksu_marker},
            },
        },
    }
    manifest["manifest_id"] = contract.digest(manifest)
    manifest_path = work / "build-manifest.json"
    contract.write_json(manifest_path, manifest)
    out_manifest = out / "build-manifest.json"
    require(not out_manifest.exists(), f"artifact already exists: {out_manifest}")
    shutil.copyfile(manifest_path, out_manifest)
    emit_output("ak3name", ak3_name)
    emit_output("artifact_name", artifact_name)
    emit_output("ksuver", (lock["resources"].get("ksu_identity") or {}).get("version_code", ""))
    emit_output("kernelrel", image_record.get("release", "debug-skipped"))
    emit_output("kernelver", image_record.get("uts_version", "debug-skipped"))
    emit_output("release_allowed", "true" if report["release_allowed"] else "false")
    print(f"manifest={manifest_path} image_sha256={image_record['sha256']}")
    print(f"artifact={out / artifact_name}")


def main():
    parser = make_parser()
    args = parser.parse_args()
    try:
        if args.fingerprint:
            fingerprint(args)
        elif args.verify_toolchain:
            verify_toolchain(args)
        elif args.dry_run:
            args.work = args.work or Path(os.environ.get("ACE6_WORK", ROOT / "work"))
            args.out = args.out or Path(os.environ.get("ACE6_OUT", ROOT / "out"))
            dry_run(args)
        else:
            build(args)
        return 0
    except (contract.Invalid, BuildError, OSError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
