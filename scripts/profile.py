#!/usr/bin/env python3
"""Ace6 profile preflight and isolated source preparation (Python stdlib only).

This is the M1 entry point, not a kernel builder or publisher. Existing build
entry points are migrated in T15 after hook/configuration contracts are ready.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SHA = re.compile(r"[0-9a-f]{40}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(Path(path).read_text(), object_pairs_hook=unique)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def inside(root, relative):
    require(isinstance(relative, str) and relative, "empty path")
    rel = Path(relative)
    require(not rel.is_absolute() and ".." not in rel.parts, f"unsafe path: {relative}")
    root = Path(root).resolve()
    path = root / rel
    require(path.resolve().is_relative_to(root), f"path escapes workspace: {relative}")
    return path


def link_spec(path, sources):
    """Read a checked-in source link declaration: SOURCE:relative/path."""
    value = Path(path).read_text(encoding="utf-8").strip()
    source, separator, relative = value.partition(":")
    require(separator and source in sources and relative, f"invalid link spec: {path}")
    inside(Path('/tmp/ace6-path-validation'), relative)
    return source, relative


def validate_schema(value, schema, path="$", root=None):
    """Validate the explicit subset used by the checked-in JSON schemas.

    Unknown schema keywords fail: unsupported constraints cannot be ignored.
    """
    root = schema if root is None else root
    supported = {"$schema", "$id", "$defs", "$ref", "title", "description", "type",
                 "properties", "required", "additionalProperties", "items", "enum",
                 "const", "pattern", "minLength", "minimum"}
    require(not set(schema) - supported, f"unsupported schema keys at {path}")
    if "$ref" in schema:
        ref = schema["$ref"]
        require(ref.startswith("#/$defs/"), "only local schema definitions supported")
        validate_schema(value, root["$defs"][ref.split("/")[-1]], path, root)
        return
    types = {"object": dict, "array": list, "string": str, "integer": int,
             "boolean": bool, "null": type(None)}
    if "type" in schema:
        names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        require(any(type(value) is types[t] for t in names), f"{path}: expected {names}")
    if "enum" in schema:
        require(value in schema["enum"], f"{path}: invalid enum {value!r}")
    if "const" in schema:
        require(type(value) is type(schema["const"]) and value == schema["const"], f"{path}: incorrect constant")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        require(set(schema.get("required", [])) <= value.keys(), f"{path}: missing required fields")
        for key, item in value.items():
            if key in props:
                validate_schema(item, props[key], f"{path}.{key}", root)
            else:
                extra = schema.get("additionalProperties", True)
                require(extra is not False, f"{path}: unknown field {key}")
                if isinstance(extra, dict):
                    validate_schema(item, extra, f"{path}.{key}", root)
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            validate_schema(item, schema["items"], f"{path}[{i}]", root)
    if isinstance(value, str):
        require(len(value) >= schema.get("minLength", 0), f"{path}: empty value")
        if "pattern" in schema:
            require(re.search(schema["pattern"], value) is not None, f"{path}: invalid format")
    if type(value) is int and "minimum" in schema:
        require(value >= schema["minimum"], f"{path}: value too small")


def profile(name, root=ROOT, seen=()):
    require(re.fullmatch(r"ace6-[a-z0-9.-]+", name) is not None and ".." not in name, "invalid profile name")
    require(name not in seen, "profile inheritance cycle")
    p = read_json(root / "profiles" / name / "profile.json")
    require(p["name"] == name, "profile name mismatch")
    if p.get("extends"):
        base = profile(p["extends"], root, (*seen, name))
        merged = copy.deepcopy(base)
        merged.update(p)
        merged["features"] = {**base["features"], **p["features"]}
        merged["capabilities"] = list(dict.fromkeys(base["capabilities"] + p["capabilities"]))
        merged["blockers"] = list(dict.fromkeys(base["blockers"] + p["blockers"]))
        return merged
    return p


def parse_value(value, spec, adapter=False):
    if adapter and spec["type"] == "boolean" and isinstance(value, str):
        require(value in ("true", "false"), "booleans must be true or false")
        value = value == "true"
    validate_schema(value, {k: v for k, v in spec.items() if k in ("type", "enum")})
    if isinstance(value, str):
        require(not any(ord(c) < 32 or ord(c) == 127 for c in value), "text contains control characters")
    return value


def legacy_arguments(arguments, root=ROOT):
    """Translate reproduce.sh's feature/identity flags without invoking a shell."""
    contract = read_json(root / "schemas/input-fields.json")
    flags = {s["legacy_cli"]: f for f, s in contract.items() if s["legacy_cli"]}
    values = {}
    i = 0
    while i < len(arguments):
        flag = arguments[i]
        require(flag in flags, f"unknown legacy feature/identity flag: {flag}")
        field = flags[flag]
        if contract[field]["type"] == "boolean":
            value = flag != "--no-attribution"
        else:
            i += 1
            require(i < len(arguments), f"{flag} requires a value")
            value = arguments[i]
        require(field not in values or values[field] == value, f"conflicting legacy flag: {flag}")
        values[field] = value
        i += 1
    return values


def normalize(raw, selected=None, root=ROOT):
    require(isinstance(raw, dict), "input must be a JSON object")
    contract = read_json(root / "schemas/input-fields.json")
    values = {}
    if "schema_version" in raw:
        validate_schema(raw, read_json(root / "schemas/config.schema.json"))
        selected_from_input = raw["version"]["profile"]
        require(selected is None or selected == selected_from_input, "conflicting profile selection")
        selected = selected_from_input
        for field, spec in contract.items():
            values[field] = parse_value(raw[spec["layer"]][field], spec)
    else:
        for key, value in raw.items():
            if key == "profile":
                require(selected is None or selected == value, "conflicting profile selection")
                selected = value
                continue
            found = [f for f, s in contract.items() if key == f or key in s["aliases"]]
            require(len(found) == 1, f"unknown input: {key}")
            field = found[0]
            parsed = parse_value(value, contract[field], adapter=True)
            require(field not in values or values[field] == parsed, f"conflicting aliases: {field}")
            values[field] = parsed
    if selected is None:
        ksu = values.get("ksu_type", "none")
        susfs = values.get("susfs", False)
        ds = values.get("droidspaces", "false")
        require(not susfs or ksu != "none", "SUSFS requires ReSukiSU")
        require(not susfs or ds == "false", "Droidspaces + SUSFS is unsupported")
        if values.get("rekernel", False):
            selected = "ace6-rekernel-experimental"
        elif ds != "false":
            selected = "ace6-droidspaces-" + ("resukisu-" if ksu != "none" else "") + ds + "-6.6"
        else:
            selected = "ace6-resukisu-susfs-inline-6.6" if susfs else ("ace6-resukisu-manual-6.6" if ksu != "none" else "ace6-minimal-6.6")
    p = profile(selected, root)
    config = {"schema_version": 1, "version": {"profile": selected}}
    for field, spec in contract.items():
        value = values.get(field, p["features"].get(field, spec["default"]))
        config.setdefault(spec["layer"], {})[field] = value
    f, out = config["features"], config["artifacts"]
    for field in ("ksu_type", "susfs", "droidspaces", "rekernel"):
        require(f[field] == p["features"][field], f"{field} conflicts with profile {selected}")
    require(not f["susfs"] or f["ksu_type"] != "none", "SUSFS requires ReSukiSU")
    require(not f["susfs"] or f["droidspaces"] == "false", "Droidspaces + SUSFS is unsupported")
    expected = "susfs-inline" if f["susfs"] else ("manual" if f["ksu_type"] != "none" else "none")
    require(p["hook_mode"] == expected, "implicit or mixed hook mode is forbidden")
    require(not f["ghost_task"] or f["droidspaces"] != "false", "ghost_task requires Droidspaces")
    require(not out["debug_skip_build"] or not (out["release_enable"] or out["ccache_update"]), "debug skip build cannot publish or update public cache")
    require(not out["release_enable"] or not p["experimental"], "experimental profile cannot be released")
    require(not out["independent_modules"] or f["ksu_type"] != "none", "KSU modules are not applicable without KSU")
    validate_schema(config, read_json(root / "schemas/config.schema.json"))
    return config, p


def validate_lock(lock, config, p, root=ROOT):
    validate_schema(lock, read_json(root / "schemas/lock.schema.json"))
    require(lock["profile"] == p["name"], "lock/profile mismatch")
    require(lock["hook_mode"] == p["hook_mode"], "lock/hook mismatch")
    require(lock["profile_sha256"] == digest(p), "profile content differs from lock")
    f = config["features"]
    required = {"kernel", "modules", "devicetrees"}
    if f["ksu_type"] != "none":
        required.add("resukisu")
    if f["susfs"]:
        required.add("susfs")
    require(required <= lock["sources"].keys(), "lock missing required source")
    for name, source in lock["sources"].items():
        require(SHA.fullmatch(source["commit"]) is not None, f"unlocked source: {name}")
        require(source["url"].startswith("https://"), f"source must use HTTPS: {name}")
        require(re.fullmatch(r"[a-zA-Z0-9_-]+", name) is not None, "invalid source name")
        inside(Path('/tmp/ace6-path-validation'), source["directory"])
        require(source["directory"] not in (".", "manifest.json", "lock.json", "failure.json"), "reserved source directory")
    directories = [Path(s["directory"]) for s in lock["sources"].values()]
    for i, directory in enumerate(directories):
        require(all(not directory.is_relative_to(other) and not other.is_relative_to(directory)
                    for other in directories[:i]), "overlapping source directories")
    clang = lock["resources"].get("clang", {})
    require(clang.get("version") and DIGEST.fullmatch(clang.get("sha256", "")), "toolchain version/hash missing")
    require(clang.get("url", "").startswith("https://"), "toolchain URL missing")
    actions = lock["resources"].get("actions", {})
    require(actions and all(SHA.fullmatch(v) for v in actions.values()), "Actions references must be full SHAs")
    for asset in lock["local_files"]:
        path = inside(root, asset["path"])
        require(path.is_file() and file_hash(path) == asset["sha256"], f"local hash mismatch: {asset['path']}")
    inventory = {a["path"]: a["sha256"] for a in lock["local_files"]}
    require(len(inventory) == len(lock["local_files"]), "duplicate local inventory entry")
    for step in lock["steps"]:
        require(step["source"] in lock["sources"], "step references missing source")
        require(step["layer"] in ("upstream", "integration", "feature"), "invalid patch layer")
        require(inventory.get(step["path"]) == step["sha256"], "step absent from hashed inventory")
        if step["operation"] in ("copy", "link"):
            inside(Path('/tmp/ace6-path-validation'), step["destination"])
        if step["operation"] == "link":
            link_spec(inside(root, step["path"]), lock["sources"])
    if f["kpm"]:
        kpm = lock["resources"].get("kpm")
        require(isinstance(kpm, dict) and kpm.get("version") and DIGEST.fullmatch(kpm.get("sha256", "")), "KPM lacks pinned version/hash")
        require(kpm.get("kernel_commit") == lock["sources"]["kernel"]["commit"], "KPM kernel compatibility is not established")
    return lock


def preflight(config, p, lock):
    blockers = list(p["blockers"]) + list(lock["blockers"])
    tasks = {"lz4_zstd": "T14", "lz4kd": "T14", "show_all_algos": "T14", "zram_writeback": "T14/T20",
             "baseband_guard": "T08", "better_net": "T14", "bbr": "T14", "ghost_task": "T10", "kpm": "T17"}
    for key, task in tasks.items():
        if config["features"][key]:
            blockers.append(f"{key}: integration/configuration contract pending {task}")
    if config["artifacts"]["release_enable"]:
        blockers.append("release: build/runtime evidence and explicit publication step pending T25-T27")
    if config["artifacts"]["artifact_mode"] in ("boot", "all"):
        blockers.append("boot.img inputs/packaging contract pending T18")
    return {
        "config_id": digest(config), "lock_id": digest(lock), "profile": p["name"],
        "hook_mode": p["hook_mode"], "prepare_allowed": not blockers,
        "blockers": list(dict.fromkeys(blockers)), "build_implemented": False,
        "runtime_status": "not-tested", "release_allowed": False,
        "notes": ["cve_patch is a compatibility no-op; no extra GhostLock patch"] if config["features"]["cve_patch"] else [],
    }


def run(args, cwd=None, include_stderr=False):
    result = subprocess.run([str(a) for a in args], cwd=cwd, text=True, capture_output=True,
                            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"}, timeout=300)
    require(result.returncode == 0, f"{args[0]} failed: {(result.stderr or result.stdout)[-6000:]}")
    return (result.stdout + (result.stderr if include_stderr else "")).strip()


def require_clean(source, commit):
    require(run(["git", "-C", source, "rev-parse", "HEAD"]) == commit, "external source HEAD differs from lock")
    require(not run(["git", "-C", source, "status", "--porcelain", "--untracked-files=all", "--ignored"]), "external source is dirty (including ignored build outputs)")
    flags = run(["git", "-C", source, "ls-files", "-v"]).splitlines()
    require(all(line.startswith("H ") for line in flags), "external source has skip-worktree/assume-unchanged entries")


def prepare(config, p, lock, work, external=None, root=ROOT):
    validate_lock(lock, config, p, root)
    report = preflight(config, p, lock)
    require(report["prepare_allowed"], "profile blocked: " + "; ".join(report["blockers"]))
    external = external or {}
    require(set(external) <= lock["sources"].keys(), "unknown external source name")
    work = Path(work).absolute()
    require(not work.exists() and not work.is_symlink(), "workspace already exists; choose a new directory")
    for name, source in external.items():
        require(not work.resolve().is_relative_to(Path(source).resolve()), "workspace must be outside external source")
        require_clean(source, lock["sources"][name]["commit"])
    work.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=work.name + ".preparing-", dir=work.parent))
    manifest = {"schema_version": 1, "phase": "preparing", "config": config,
                "config_id": digest(config), "lock_id": digest(lock), "sources": {}, "steps": [],
                "build": "not-run", "runtime": "not-tested", "artifacts": [],
                "reproducibility": {"source_preparation": False, "byte_identical_build": False}}
    try:
        for name, source in lock["sources"].items():
            dest = inside(stage, source["directory"])
            require(not dest.exists(), "overlapping source destinations")
            if name in external:
                run(["git", "clone", "--no-local", "--no-checkout", external[name], dest])
            else:
                run(["git", "init", dest])
                run(["git", "-C", dest, "remote", "add", "origin", source["url"]])
                run(["git", "-C", dest, "fetch", "--depth=1", "origin", source["commit"]])
            run(["git", "-C", dest, "checkout", "--detach", source["commit"]])
            require(run(["git", "-C", dest, "rev-parse", "HEAD"]) == source["commit"], "resolved SHA differs")
            entries = run(["git", "-C", dest, "ls-files", "--stage"]).splitlines()
            require(not any(line.startswith("160000 ") for line in entries), "submodules need explicit lock/resolver support")
            manifest["sources"][name] = {"commit": source["commit"], "tree": run(["git", "-C", dest, "rev-parse", "HEAD^{tree}"])}
        for number, step in enumerate(lock["steps"]):
            dest = inside(stage, lock["sources"][step["source"]]["directory"])
            patch = inside(root, step["path"])
            require(file_hash(patch) == step["sha256"], "step hash changed during prepare")
            entry = {"index": number, "path": step["path"], "sha256": step["sha256"], "status": "running"}
            manifest["steps"].append(entry)
            if step["operation"] == "patch":
                run(["git", "apply", "--check", patch], cwd=dest)
                entry["log"] = run(["git", "apply", "--verbose", patch], cwd=dest, include_stderr=True)
            elif step["operation"] == "copy":
                target = inside(dest, step["destination"])
                require(not target.is_symlink(), "refusing to overwrite symlink")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(patch, target)
            else:
                source_name, source_path = link_spec(patch, lock["sources"])
                origin = inside(stage, lock["sources"][source_name]["directory"] + "/" + source_path)
                require(origin.exists() and not origin.is_symlink(), "link origin is missing or symlinked")
                target = inside(dest, step["destination"])
                require(not target.exists() and not target.is_symlink(), "refusing to overwrite existing link target")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(os.path.relpath(origin, target.parent), target_is_directory=origin.is_dir())
                entry["target"] = f"{source_name}:{source_path}"
            entry["status"] = "applied"
        for name, source in lock["sources"].items():
            dest = inside(stage, source["directory"])
            run(["git", "-C", dest, "add", "-A"])
            manifest["sources"][name]["prepared_tree"] = run(["git", "-C", dest, "write-tree"])
        manifest["phase"] = "sources-prepared"
        manifest["reproducibility"]["source_preparation"] = True
        manifest["manifest_id"] = digest(manifest)
        validate_schema(manifest, read_json(root / "schemas/manifest.schema.json"))
        write_json(stage / "manifest.json", manifest)
        write_json(stage / "lock.json", lock)
        # rename does not merge with an existing workspace; never reuse old Image.
        require(not work.exists(), "workspace appeared during preparation")
        stage.rename(work)
        return manifest
    except Exception as exc:
        manifest["phase"] = "failed"
        manifest["error"] = str(exc)
        write_json(stage / "failure.json", manifest)
        raise Invalid(f"preparation stopped; isolated failure record: {stage / 'failure.json'}; {exc}") from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["normalize", "check", "prepare"])
    parser.add_argument("--inputs", type=Path, help="legacy flat inputs or normalized JSON")
    parser.add_argument("--profile")
    parser.add_argument("--lock", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--work", type=Path)
    parser.add_argument("--source", action="append", default=[], metavar="NAME=PATH")
    parser.add_argument("--legacy-args", nargs=argparse.REMAINDER, help="reproduce.sh feature/identity flags (last argument group)")
    args = parser.parse_args()
    try:
        require(args.inputs is None or args.legacy_args is None, "choose --inputs or --legacy-args")
        raw = legacy_arguments(args.legacy_args) if args.legacy_args is not None else (read_json(args.inputs) if args.inputs else {})
        config, p = normalize(raw, args.profile)
        result = config
        code = 0
        if args.command != "normalize":
            lock = read_json(args.lock or ROOT / "manifests/locks" / (p["name"] + ".lock.json"))
            validate_lock(lock, config, p)
            result = preflight(config, p, lock)
            code = 0 if result["prepare_allowed"] else 2
            if args.command == "prepare":
                require(args.work is not None, "prepare requires --work")
                external = {}
                for item in args.source:
                    key, sep, value = item.partition("=")
                    require(sep and key not in external and value, "invalid/duplicate --source")
                    external[key] = value
                if os.environ.get("KERNEL_SRC"):
                    require("kernel" not in external, "KERNEL_SRC conflicts with --source kernel")
                    external["kernel"] = os.environ["KERNEL_SRC"]
                result = prepare(config, p, lock, args.work, external)
        if args.output:
            require(not args.output.exists(), "output exists; choose a new path")
            write_json(args.output, result)
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        return code
    except (Invalid, OSError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
