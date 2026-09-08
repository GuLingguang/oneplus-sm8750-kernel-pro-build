#!/usr/bin/env python3
"""Run the repository-only Ace6 CI gate.

This gate deliberately performs no network access, source checkout, kernel
compilation, device access, release publication, or cache mutation.  The
manual build workflow owns those operations; this command checks that the
inputs and entrypoints are internally consistent before that workflow runs.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "work" / "_tmp" / "ci"
sys.path.insert(0, str(ROOT / "scripts"))
import profile as profile_rules  # noqa: E402


class CIError(RuntimeError):
    """A repository CI check failed."""


def run(command, *, cwd=ROOT, capture=False):
    result = subprocess.run(
        [str(item) for item in command],
        cwd=str(cwd),
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        text=True,
        capture_output=capture,
        check=False,
    )
    if result.returncode:
        detail = ((result.stderr or "") + (result.stdout or ""))[-6000:]
        raise CIError(f"{' '.join(map(str, command))} failed ({result.returncode}): {detail}")
    return result.stdout if capture else ""


def check_profiles_and_locks():
    profiles = sorted((ROOT / "profiles").glob("*/profile.json"))
    if not profiles:
        raise CIError("no profiles found")

    profile_names = {path.parent.name for path in profiles}
    lock_paths = sorted((ROOT / "manifests" / "locks").glob("*.lock.json"))
    lock_names = {path.name.removesuffix(".lock.json") for path in lock_paths}
    if profile_names != lock_names:
        raise CIError(f"profile/lock set differs: profiles={sorted(profile_names)} locks={sorted(lock_names)}")

    for profile_path in profiles:
        name = profile_path.parent.name
        config, profile = profile_rules.normalize({}, name)
        lock = profile_rules.read_json(ROOT / "manifests" / "locks" / f"{name}.lock.json")
        profile_rules.validate_lock(lock, config, profile)
        report = profile_rules.preflight(config, profile, lock, phase="build")
        if report["profile"] != name or report["config_id"] != profile_rules.digest(config):
            raise CIError(f"preflight identity mismatch: {name}")


def check_build_smoke_plans():
    TMP.mkdir(parents=True, exist_ok=True)
    for name in ("ace6-minimal-6.6", "ace6-main-release-compat-6.6"):
        output = run(
            [sys.executable, "scripts/build.py", "--profile", name, "--dry-run"],
            capture=True,
        )
        try:
            report = json.loads(output)
        except json.JSONDecodeError as exc:
            raise CIError(f"invalid dry-run JSON for {name}: {exc}") from exc
        if report["profile"] != name or not re.fullmatch(r"[0-9a-f]{64}", report["config_id"]):
            raise CIError(f"invalid dry-run identity for {name}")
        (TMP / f"{name}.dry-run.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def check_shell_entrypoints():
    candidates = [ROOT / "reproduce.sh", ROOT / "check_upstream.sh", ROOT / "ak3" / "anykernel.sh"]
    candidates.extend(sorted((ROOT / "scripts").glob("*.sh")))
    candidates.extend(sorted((ROOT / "modules").glob("*/*.sh")))
    for path in candidates:
        if not path.is_file():
            continue
        run(["bash", "-n", path])


def check_workflows():
    sha = re.compile(r"^[0-9a-f]{40}$")
    for path in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = re.search(r"\buses:\s*([^\s#]+)", line)
            if not match:
                continue
            reference = match.group(1).rsplit("@", 1)[-1]
            if not sha.fullmatch(reference):
                raise CIError(f"workflow action is not pinned to a full SHA: {path}:{line_number}")
        text = path.read_text(encoding="utf-8")
        if path.name == "build.yml" and "scripts/build.py --workflow" not in text:
            raise CIError("build workflow does not use the common build entrypoint")


def check_generated_tree():
    forbidden = []
    for path in (ROOT / "modules").rglob("*"):
        if path.is_dir() and path.name == "node_modules":
            forbidden.append(str(path.relative_to(ROOT)))
    if forbidden:
        raise CIError("generated WebUI dependencies are present: " + ", ".join(forbidden))

    tracked = run(["git", "ls-files"], capture=True).splitlines()
    generated_markers = ("/__pycache__/", "/node_modules/", ".pyc")
    stale_tracked = []
    for item in tracked:
        normalized = "/" + item.replace(os.sep, "/") + "/"
        if any(marker in normalized for marker in generated_markers):
            # During the local normalization pass, intentionally removed
            # generated files are allowed to remain as unstaged deletions until
            # the user reviews and commits the cleanup.
            if (ROOT / item).exists():
                stale_tracked.append(item)
    if stale_tracked:
        raise CIError("generated files are still present in the worktree: " + ", ".join(stale_tracked))


def check_git_whitespace():
    # Integration patch files contain a second diff whose added lines preserve
    # upstream kernel indentation. Treat that nested patch payload as data;
    # check repository-authored text around it for whitespace errors.
    run(["git", "diff", "--check", "--", ".", ":(exclude)patches/integration/*.patch"])


def main():
    checks = (
        ("profiles and locks", check_profiles_and_locks),
        ("build dry-run plans", check_build_smoke_plans),
        ("shell entrypoints", check_shell_entrypoints),
        ("workflow pinning", check_workflows),
        ("generated tree", check_generated_tree),
        ("git whitespace", check_git_whitespace),
    )
    for label, check in checks:
        check()
        print(f"PASS {label}")
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"])
    print("PASS unit tests")
    print("CI gate passed")


if __name__ == "__main__":
    try:
        main()
    except (CIError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f"CI ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
