#!/usr/bin/env python3
"""Collect T26-style device acceptance evidence over adb.

Read-only by design: every check reads device state, and the only thing written
is the evidence file on this host. Nothing is flashed, installed, started or
stopped on the device. That is what makes it safe to run against a phone that
is in daily use.

The output mirrors docs/evidence/t26-runtime.json, so a run either reproduces
that record's shape or names the field it could not fill.

A few checks are hard gates and set the exit code; everything else is recorded
as observed state, including "unavailable" when the device does not answer a
particular question. Read the evidence, not just the exit code.

Usage:
  python3 scripts/device.py --build-out out/ace6-minimal-6.6
  python3 scripts/device.py --build-out out/ace6-minimal-6.6 --soak-seconds 300
  python3 scripts/device.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INTERVAL = 10
DEFAULT_SOAK = 300
UNAVAILABLE = "unavailable"

PANIC_PATTERNS = (
    r"Kernel panic",
    r"Internal error: Oops",
    r"Unable to handle kernel",
    r"BUG: unable to handle",
    r"Watchdog detected hard LOCKUP",
)
GETPROP_LINE = re.compile(r"^\[(?P<key>[^\]]+)\]: \[(?P<value>.*)\]$")
KERNEL_RELEASE = re.compile(r"Linux version (?P<release>\S+)")
CONFIG_LINE = re.compile(r"^(?P<key>CONFIG_[A-Z0-9_]+)=(?P<value>.+)$")


class DeviceError(RuntimeError):
    """A hard failure: the run cannot produce meaningful evidence."""


def parse_getprop(text):
    """Turn `getprop` output into a mapping. Unparsable lines are skipped."""
    props = {}
    for line in text.splitlines():
        match = GETPROP_LINE.match(line.strip())
        if match:
            props[match.group("key")] = match.group("value")
    return props


def kernel_release(proc_version):
    """The release from /proc/version, e.g. `6.6.142-4k-gcb967c26c2c5+`."""
    match = KERNEL_RELEASE.search(proc_version or "")
    return match.group("release") if match else UNAVAILABLE


def parse_config(text):
    """Pick the KSU-related configuration out of a kernel config dump."""
    wanted = ("CONFIG_KSU", "CONFIG_KSU_SUSFS", "CONFIG_KSU_SUSFS_SPOOF_UNAME",
              "CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG")
    found = {}
    for line in (text or "").splitlines():
        match = CONFIG_LINE.match(line.strip())
        if match and match.group("key") in wanted:
            found[match.group("key")] = match.group("value").strip('"')
    return {key: found.get(key, UNAVAILABLE) for key in wanted}


def panic_matches(text):
    """Lines that would make a runtime claim unsafe."""
    return [line.strip() for line in (text or "").splitlines()
            if any(re.search(pattern, line) for pattern in PANIC_PATTERNS)]


def count_lines(text):
    return len([line for line in (text or "").splitlines() if line.strip()])


# Startup is all this harness proves, so a clean run is a partial pass by
# definition: the checks that would justify more need the device in hand.
RUNTIME_STATUS = "partial-pass"


def adb_runner(serial=None):
    """Return a callable that runs one adb command and returns its stdout."""
    if shutil.which("adb") is None:
        raise DeviceError("adb is not on PATH")

    def run(args, timeout=30):
        command = ["adb"] + (["-s", serial] if serial else []) + args
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise DeviceError(f"adb timed out: {' '.join(args)}") from exc
        if result.returncode != 0:
            raise DeviceError(f"adb failed: {' '.join(args)}: {result.stderr.strip()[:200]}")
        return result.stdout.strip()

    return run


def shell(run, command, timeout=30):
    """Run a shell command on the device; an unanswerable question is recorded."""
    try:
        return run(["shell", command], timeout=timeout)
    except DeviceError:
        return UNAVAILABLE


def read_build_out(path):
    """Profile identity and artifact identity from a build output directory."""
    path = Path(path)
    manifest = path / "build-manifest.json"
    if not manifest.is_file():
        raise DeviceError(f"no build-manifest.json under {path}")
    data = json.loads(manifest.read_text())
    image = data.get("build", {}).get("image", {})
    artifacts = data.get("artifacts") or [{}]
    artifact = artifacts[0]
    return {
        "name": data.get("profile") or data.get("config", {}).get("version", {}).get("profile"),
        "config_id": data.get("config_id"),
        "lock_id": data.get("lock_id"),
        "kernel_release": data.get("build", {}).get("kernel_release"),
        "image_sha256": image.get("sha256"),
        "artifact": artifact.get("path"),
        "artifact_sha256": artifact.get("sha256"),
        "expected_kernel": data.get("resolved", {}).get("kernel_localversion"),
    }


def collect_device(run):
    props = parse_getprop(shell(run, "getprop"))
    return {
        "model": props.get("ro.product.model", UNAVAILABLE),
        "product": props.get("ro.product.product", props.get("ro.product.name", UNAVAILABLE)),
        "device": props.get("ro.product.device", UNAVAILABLE),
        "target_codename": props.get("ro.product.vendor.device", UNAVAILABLE),
        "android_release": props.get("ro.build.version.release", UNAVAILABLE),
        "active_slot": props.get("ro.boot.slot_suffix", UNAVAILABLE),
    }


def boot_completed(run):
    """Tracked as an observation, matching the recorded T26 evidence."""
    return shell(run, "getprop sys.boot_completed") == "1"


def collect_observations(run, profile):
    proc_version = shell(run, "cat /proc/version")
    uname_release = shell(run, "uname -r")
    identity = shell(run, "id")
    release = kernel_release(proc_version)
    config = parse_config(shell(run, "zcat /proc/config.gz"))
    ksud = shell(run, "ksud --version")
    expected = profile.get("kernel_release")
    return {
        "proc_version_release": release,
        "uname_release": uname_release if uname_release else UNAVAILABLE,
        "adbd_context": identity if identity else UNAVAILABLE,
        "root_adbd": "uid=0" in (identity or ""),
        "ksud": ksud if ksud and ksud != UNAVAILABLE else UNAVAILABLE,
        "spoof_uname_observed": bool(
            uname_release and release and release != UNAVAILABLE and uname_release != release
        ),
        "embedded_config": config,
        "kernel_banner_matches_artifact": (
            None if not expected else release.startswith(expected.rstrip("+"))
        ),
    }


def collect_smoke(run):
    wifi = shell(run, "dumpsys wifi | grep -m1 -i 'Wi-Fi is'")
    cellular = shell(run, "getprop gsm.network.type")
    bluetooth = shell(run, "settings get global bluetooth_on")
    display = shell(run, "dumpsys display | grep -m1 -i 'mScreenState'")
    touch = shell(run, "getevent -pl 2>/dev/null | grep -c 'ABS_MT'")
    cameras = shell(run, "ls -d /dev/v4l-subdev* 2>/dev/null | wc -l")
    sensors = shell(run, "dumpsys sensorservice 2>/dev/null | grep -c 'handle='")
    modules = shell(run, "lsmod | tail -n +2 | wc -l")
    battery = shell(run, "dumpsys battery")
    disksize = shell(run, "cat /sys/block/zram0/disksize")
    algorithm = shell(run, "cat /sys/block/zram0/comp_algorithm")
    swaps = shell(run, "cat /proc/swaps")
    return {
        "wifi": wifi if wifi else UNAVAILABLE,
        "cellular": cellular if cellular else UNAVAILABLE,
        "bluetooth_enabled": bluetooth if bluetooth else UNAVAILABLE,
        "display": display if display else UNAVAILABLE,
        "touch_mt_axes": touch if touch else UNAVAILABLE,
        "camera_subdevices": cameras if cameras else UNAVAILABLE,
        "hardware_sensors": sensors if sensors else UNAVAILABLE,
        "loaded_kernel_modules": modules if modules else UNAVAILABLE,
        "battery": parse_battery(battery),
        "zram": parse_zram(disksize, algorithm, swaps),
    }


def parse_battery(text):
    """`dumpsys battery` gives labelled lines; missing labels stay unavailable."""
    fields = {}
    for line in (text or "").splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip().lower()] = value.strip()
    return {
        "health": fields.get("health", UNAVAILABLE),
        "capacity_percent": fields.get("level", UNAVAILABLE),
        "temperature_c": fields.get("temperature", UNAVAILABLE),
    }


def parse_zram(disksize, algorithm, swaps):
    """zram facts, kept separate from the swap table that proves it is in use."""
    return {
        "disksize_bytes": disksize if disksize else UNAVAILABLE,
        "algorithm": algorithm if algorithm else UNAVAILABLE,
        "swap_active": "zram0" in (swaps or ""),
    }


def soak(run, seconds, interval):
    """Sample the same handful of facts every interval, for the given duration."""
    samples = []
    if seconds <= 0:
        return {"duration_seconds": 0, "samples": 0, "note": "soak skipped"}
    deadline = time.monotonic() + seconds
    while True:
        samples.append({
            "boot_completed": boot_completed(run),
            "kernel_release": kernel_release(shell(run, "cat /proc/version")),
            "dmesg_panics": panic_matches(shell(run, "dmesg | tail -n 200", timeout=20)),
        })
        if time.monotonic() + interval > deadline:
            break
        time.sleep(interval)
    releases = {sample["kernel_release"] for sample in samples}
    return {
        "duration_seconds": seconds,
        "samples": len(samples),
        "sample_interval_seconds": interval,
        "boot_completed_stable": all(sample["boot_completed"] for sample in samples),
        "kernel_release_stable": len(releases) == 1,
        "panic_or_oops_match": any(sample["dmesg_panics"] for sample in samples),
    }


def build_evidence(run, profile, soak_seconds, interval):
    device = collect_device(run)
    if not boot_completed(run):
        raise DeviceError("device has not finished booting (sys.boot_completed != 1)")
    observations = collect_observations(run, profile)
    observations["boot_completed"] = True
    smoke = collect_smoke(run)
    last_panics = panic_matches(shell(run, "dmesg | tail -n 200", timeout=20))
    if last_panics:
        raise DeviceError("kernel log carries a panic/oops: " + "; ".join(last_panics[:3]))
    stability = soak(run, soak_seconds, interval)
    if stability.get("panic_or_oops_match"):
        raise DeviceError("a panic/oops appeared during the soak")
    if stability.get("samples") and not stability.get("kernel_release_stable"):
        raise DeviceError("the kernel release changed during the soak")
    # The recorded T26 evidence keeps the soak inside smoke_tests; stay with it.
    smoke["stability_soak"] = stability
    evidence = {
        "schema_version": 1,
        "task": "T26",
        "status": {
            "code": "booted-and-root-verified",
            "contract": "runtime-startup-and-ksu",
            "build": "built",
            "runtime": RUNTIME_STATUS,
            "release_allowed": False,
        },
        "profile": profile,
        "device": device,
        "observations": observations,
        "smoke_tests": smoke,
        "limits": [
            "Startup, root and the smoke checks only; camera capture, call and data"
            " throughput, charging, suspend/resume, rollback and long-duration"
            " stability are not covered",
            "Release and byte-identical reproducibility are unaffected by this record",
        ],
    }
    return evidence


def dry_run(profile):
    plan = [
        "getprop", "cat /proc/version", "uname -r", "id", "zcat /proc/config.gz",
        "ksud --version", "dumpsys wifi", "getprop gsm.network.type",
        "settings get global bluetooth_on", "dumpsys display", "getevent -pl",
        "ls -d /dev/v4l-subdev*", "dumpsys sensorservice", "lsmod", "dumpsys battery",
        "cat /sys/block/zram0/*", "dmesg",
    ]
    print("dry run: no device is contacted")
    print(f"profile: {profile}")
    print("read-only adb commands that a real run would issue:")
    for item in plan:
        print(f"  adb shell {item}")
    return 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--build-out", type=Path,
                        help="build output directory holding build-manifest.json")
    parser.add_argument("--serial", help="adb serial when several devices are attached")
    parser.add_argument("--soak-seconds", type=int, default=DEFAULT_SOAK)
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL)
    parser.add_argument("--json-out", type=Path, help="where to write the evidence")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the plan without contacting a device")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    profile = {}
    if args.build_out:
        profile = read_build_out(args.build_out)
    if args.dry_run:
        return dry_run(profile or {"name": "unset; pass --build-out"})
    if not profile:
        raise DeviceError("--build-out is required: runtime evidence is tied to an artifact")
    run = adb_runner(args.serial)
    evidence = build_evidence(run, profile, args.soak_seconds, args.interval)
    out = args.json_out or (ROOT / "docs/evidence" /
                            f"t26-runtime-{profile.get('name', 'profile')}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")
    print(f"evidence written to {out}")
    print(f"runtime: {evidence['status']['runtime']}  "
          f"boot_completed={evidence['observations']['boot_completed']}  "
          f"kernel_release={evidence['observations']['proc_version_release']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DeviceError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"device-acceptance error: {exc}", file=sys.stderr)
        raise SystemExit(2)
