#!/usr/bin/env python3
"""Cumulative profile drift checker.

The checker is intentionally report-only. It never edits a lock, source
provider, GitHub issue, or release. A candidate source is compared with a
locked baseline by applying each profile's ordered lock steps cumulatively.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PROJECT_TMP = ROOT / "work" / "_tmp"
sys.path.insert(0, str(ROOT / "scripts"))
import build as common_build  # noqa: E402
import profile as profile_rules  # noqa: E402


def command(argv, cwd=None):
    result = subprocess.run(
        [str(item) for item in argv], cwd=str(cwd) if cwd else None,
        text=True, capture_output=True, check=False,
    )
    return result.returncode, (result.stdout or "") + (result.stderr or "")


def source_identity(path: Path):
    sha = ""
    dirty = None
    code, output = command(["git", "-C", path, "rev-parse", "HEAD"])
    if code == 0:
        sha = output.strip().splitlines()[-1] if output.strip() else ""
        code, status = command(["git", "-C", path, "status", "--porcelain", "--untracked-files=all"])
        dirty = code != 0 or bool(status.strip())
    return {"path": str(path), "sha": sha or None, "dirty": dirty}


def safe_extract_tar(archive: Path, destination: Path):
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, mode="r:gz") as stream:
        members = stream.getmembers()
        for member in members:
            relative = Path(member.name)
            if relative.is_absolute() or ".." in relative.parts:
                raise RuntimeError(f"unsafe archive member: {member.name}")
            target = (destination / relative).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise RuntimeError(f"archive member escapes destination: {member.name}")
        stream.extractall(destination)
    roots = sorted({Path(member.name).parts[0] for member in members if member.name and Path(member.name).parts})
    if len(roots) != 1:
        raise RuntimeError(f"archive has unexpected top-level entries: {roots}")
    return destination / roots[0]


def fetch_archive(repo: str, ref: str, destination: Path, mirror_prefix: str = ""):
    origin = f"https://github.com/{repo}/archive/{ref}.tar.gz"
    url = mirror_prefix.rstrip("/") + "/" + origin if mirror_prefix else origin
    archive = destination / "source.tar.gz"
    destination.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": "ace6-drift-check/1"})
    with urlopen(request, timeout=180) as response, archive.open("wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
    return safe_extract_tar(archive, destination / "source")


def remote_ref(repo: str, branch: str, mirror_prefix: str = ""):
    origin = f"https://github.com/{repo}.git"
    url = mirror_prefix.rstrip("/") + "/" + origin if mirror_prefix else origin
    code, output = command(["git", "ls-remote", url, f"refs/heads/{branch}"])
    if code != 0:
        raise RuntimeError(f"cannot resolve candidate branch: {output[-4000:]}")
    match = re.search(r"^([0-9a-f]{40})\s+refs/heads/", output, re.MULTILINE)
    if not match:
        raise RuntimeError(f"candidate branch has no usable SHA: {branch}")
    return match.group(1)


def parse_source_args(values):
    result = {}
    for value in values:
        name, separator, path = value.partition("=")
        if not separator or not name or not path:
            raise ValueError(f"source must be NAME=PATH: {value}")
        result[name] = Path(path).expanduser().resolve()
    return result


def copy_snapshot(source: Path, destination: Path):
    if not source.is_dir():
        raise RuntimeError(f"source tree is missing: {source}")
    code, _ = command(["git", "-C", source, "rev-parse", "--git-dir"])
    if code == 0:
        code, output = command([
            "git", "clone", "--local", "--shared", "--no-checkout", "--quiet",
            source, destination,
        ])
        if code != 0:
            raise RuntimeError(f"cannot clone source snapshot: {output[-4000:]}")
        code, output = command(["git", "-C", destination, "checkout", "--detach", "--quiet", "HEAD"])
        if code != 0:
            raise RuntimeError(f"cannot materialize source snapshot: {output[-4000:]}")
        return
    shutil.copytree(source, destination, symlinks=True,
                    ignore=shutil.ignore_patterns(".git", ".gitignore"))


def step_record(step, status, category=None, detail=""):
    value = {
        "path": step["path"], "operation": step["operation"],
        "source": step["source"], "layer": step["layer"], "status": status,
    }
    if category:
        value["category"] = category
    if detail:
        value["detail"] = detail[-4000:]
    return value


def apply_steps(kernel: Path, lock, config, source_roots):
    records = []
    steps = list(lock["steps"])
    for feature, paths in common_build.FEATURE_PATCHES.items():
        if config["features"].get(feature):
            steps.extend({
                "source": "kernel", "operation": "patch", "layer": "feature",
                "path": path, "sha256": profile_rules.file_hash(ROOT / path), "destination": "",
            } for path in paths)
    for step in steps:
        patch = ROOT / step["path"]
        if not patch.is_file() or profile_rules.file_hash(patch) != step["sha256"]:
            records.append(step_record(step, "failed", "local-input-drift", "local input missing or hash differs"))
            return records, "failed"
        if step["source"] != "kernel":
            records.append(step_record(step, "incomplete", "unsupported-source-step", "only kernel target steps are supported by this checker"))
            return records, "incomplete"
        if step["operation"] == "patch":
            code, output = command(["git", "apply", "--check", str(patch)], cwd=kernel)
            if code != 0:
                records.append(step_record(step, "failed", "patch-apply-failure-needs-review", output))
                return records, "failed"
            code, output = command(["git", "apply", "--verbose", str(patch)], cwd=kernel)
            if code != 0:
                records.append(step_record(step, "failed", "patch-apply-failure-needs-review", output))
                return records, "failed"
            records.append(step_record(step, "applied"))
            continue
        if step["operation"] == "copy":
            target = kernel / step["destination"]
            if target.is_symlink():
                records.append(step_record(step, "failed", "destination-symlink", str(target)))
                return records, "failed"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(patch, target)
            records.append(step_record(step, "applied"))
            continue
        if step["operation"] == "link":
            source_name, relative = profile_rules.link_spec(patch, lock["sources"])
            origin_root = source_roots.get(source_name)
            if origin_root is None:
                records.append(step_record(step, "incomplete", "missing-source-provider", f"provider not supplied: {source_name}"))
                return records, "incomplete"
            origin = (origin_root / relative).resolve()
            if not origin.is_file() and not origin.is_dir():
                records.append(step_record(step, "failed", "link-origin-missing", str(origin)))
                return records, "failed"
            target = kernel / step["destination"]
            if target.exists() or target.is_symlink():
                records.append(step_record(step, "failed", "link-destination-exists", str(target)))
                return records, "failed"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(origin, target_is_directory=origin.is_dir())
            records.append(step_record(step, "applied", detail=f"{source_name}:{relative}"))
            continue
        records.append(step_record(step, "failed", "unknown-operation", step["operation"]))
        return records, "failed"
    return records, "passed"


def rule_checks(kernel: Path, config):
    makefile = kernel / "Makefile"
    text = makefile.read_text(encoding="utf-8", errors="replace") if makefile.is_file() else ""
    version = {
        "status": "passed" if re.search(r"^VERSION\s*=\s*6\s*$", text, re.MULTILINE)
        and re.search(r"^PATCHLEVEL\s*=\s*6\s*$", text, re.MULTILINE) else "failed",
        "expected": "6.6",
    }
    anchors = []
    if config["features"].get("droidspaces") != "false":
        anchors.extend(["drivers/misc/ntsync.c", "include/uapi/linux/ntsync.h"])
    if config["features"].get("ksu_type") != "none":
        anchors.append("drivers/kernelsu")
    if config["features"].get("susfs"):
        anchors.extend(["fs/susfs.c", "include/linux/susfs.h", "include/linux/susfs_def.h"])
    if config["features"].get("rekernel"):
        anchors.append("drivers/rekernel")
    missing = [path for path in anchors if not (kernel / path).exists()]
    consumers = {"status": "passed" if not missing else "failed", "anchors": anchors, "missing": missing}
    config_status = "not-run" if not (kernel / ".config").is_file() else "present-not-revalidated"
    return {"version": version, "type_and_consumer": consumers, "config": {"status": config_status}}


def check_variant(config, lock, profile, source: Path, source_roots, label, temp_root):
    identity = source_identity(source)
    snapshot = temp_root / label
    copy_snapshot(source, snapshot)
    steps, status = apply_steps(snapshot, lock, config, source_roots)
    checks = rule_checks(snapshot, config) if status == "passed" and not profile["blockers"] else {}
    if status == "passed" and profile["blockers"]:
        status = "blocked"
    if status == "passed" and any(item.get("status") == "failed" for item in checks.values()):
        status = "failed"
    expected = lock["sources"]["kernel"]["commit"]
    if label == "baseline" and identity["sha"] != expected:
        category = "locked-baseline-mismatch"
    elif label == "candidate" and identity["sha"] and identity["sha"] != expected:
        category = "candidate-source-identity-drift"
    else:
        category = "none"
    return {
        "source": identity, "expected_kernel_commit": expected,
        "status": status, "identity_category": category,
        "steps": steps, "contracts": checks,
    }


def profile_result(name, profile, baseline, candidate):
    classes = []
    if baseline["identity_category"] != "none":
        classes.append(baseline["identity_category"])
    if candidate["identity_category"] != "none":
        classes.append(candidate["identity_category"])
    if baseline["status"] in ("failed", "incomplete"):
        classes.append("locked-baseline-check-incomplete-or-failed")
    elif baseline["status"] == "blocked":
        classes.append("profile-blocked-by-existing-rule")
    if candidate["status"] == "failed":
        classes.append("patch-apply-failure-needs-review")
    elif candidate["status"] == "incomplete":
        classes.append("missing-source-provider")
    elif candidate["status"] == "blocked":
        classes.append("profile-blocked-by-existing-rule")
    elif baseline["status"] == "passed" and candidate["status"] == "passed":
        classes.append("no-observed-drift")
        if candidate["identity_category"] != "none":
            classes.append("semantic-review-required; not evidence of upstream-absorption")
    return {
        "profile": name, "baseline": baseline, "candidate": candidate,
        "classification": list(dict.fromkeys(classes)) or ["unclassified-review"],
    }


def markdown(report):
    lines = [
        "# Ace6 upstream drift report", "",
        f"Generated: `{report['generated_utc']}`", "",
        "This report is advisory and does not edit locks or create Issues.", "",
        "| Profile | Baseline | Candidate | Classification |",
        "| --- | --- | --- | --- |",
    ]
    for item in report["profiles"]:
        lines.append("| `{}` | `{}` | `{}` | {} |".format(
            item["profile"], item["baseline"]["status"], item["candidate"]["status"],
            ", ".join(item["classification"]),
        ))
    lines.extend([
        "", "## Interpretation", "",
        "A patch failure is only a review trigger. It is not evidence that upstream",
        "absorbed the change; compare the semantic consumer and configuration",
        "rules before dropping or adapting a patch.", "", "## Reproduction", "",
        "```sh",
        "./check_upstream.sh --local /absolute/candidate/kernel --baseline /absolute/locked/kernel",
        "```",
    ])
    return "\n".join(lines) + "\n"


def issue_draft(report):
    lines = [
        "# Upstream drift review draft", "",
        "This is a draft only. The checker does not create, comment on, or close Issues.", "",
        f"Candidate: `{report['candidate']['kernel']['sha'] or 'unknown'}`",
        f"Locked commit: `{report['candidate']['kernel']['expected_commit']}`", "",
    ]
    for item in report["profiles"]:
        lines.append(f"- `{item['profile']}`: " + ", ".join(item["classification"]))
    lines.extend([
        "", "## Required review", "",
        "- classify each failed patch as context/API/type/configuration drift or",
        "  equivalent upstream implementation only after semantic inspection;",
        "- attach the cumulative check log and affected consumer/configuration rule;",
        "- update a lock only in a separate explicitly reviewed change.", "",
    ])
    return "\n".join(lines)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", action="append", dest="profiles", help="profile name; repeatable")
    parser.add_argument("--candidate-kernel", type=Path)
    parser.add_argument("--baseline-kernel", type=Path)
    parser.add_argument("--local", type=Path, help="compatibility alias for --candidate-kernel")
    parser.add_argument("--source", action="append", default=[], metavar="NAME=PATH")
    parser.add_argument("--fetch-candidate", action="store_true")
    parser.add_argument("--repo", default="Ace6-Development/android_kernel_oneplus_sm8750")
    parser.add_argument("--branch", default="lineage-23.2")
    parser.add_argument("--mirror-prefix", default="")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    parser.add_argument("--issue-draft", type=Path)
    parser.add_argument("--ci", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    names = args.profiles or sorted(path.parent.name for path in (ROOT / "profiles").glob("*/profile.json"))
    source_args = parse_source_args(args.source)
    candidate = args.candidate_kernel or args.local
    PROJECT_TMP.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.TemporaryDirectory(prefix="ace6-drift-", dir=PROJECT_TMP)
    temp_root = Path(temporary.name)
    fetched = {}
    candidate_commit = None
    try:
        selected = []
        for name in names:
            config, profile = profile_rules.normalize({}, name)
            lock = profile_rules.read_json(ROOT / "manifests/locks" / f"{name}.lock.json")
            profile_rules.validate_lock(lock, config, profile)
            selected.append((name, config, lock, profile))
        kernel_commits = {lock["sources"]["kernel"]["commit"] for _, _, lock, _ in selected}
        if len(kernel_commits) != 1:
            raise RuntimeError("selected profiles do not share one kernel lock commit")
        locked_commit = next(iter(kernel_commits))
        if args.fetch_candidate:
            candidate_commit = remote_ref(args.repo, args.branch, args.mirror_prefix)
            candidate = fetch_archive(args.repo, args.branch, temp_root / "candidate", args.mirror_prefix)
            fetched["candidate"] = str(candidate)
            baseline = (args.baseline_kernel.expanduser().resolve() if args.baseline_kernel else
                        fetch_archive(args.repo, locked_commit, temp_root / "baseline", args.mirror_prefix))
            fetched["baseline"] = str(baseline)
        else:
            baseline = args.baseline_kernel.expanduser().resolve() if args.baseline_kernel else None
            candidate = candidate.expanduser().resolve() if candidate else None
            if baseline is None and candidate is not None:
                baseline = candidate
            if candidate is None:
                raise RuntimeError("candidate source is required (use --candidate-kernel, --local, or --fetch-candidate)")
        provider_roots = dict(source_args)
        link_sources = set()
        for _, _, lock, _ in selected:
            for step in lock["steps"]:
                if step["operation"] == "link":
                    source_name, _ = profile_rules.link_spec(ROOT / step["path"], lock["sources"])
                    link_sources.add(source_name)
        for source_name in sorted(link_sources - provider_roots.keys()):
            if not args.fetch_candidate:
                continue
            source_spec = selected[0][2]["sources"][source_name]
            repo = source_spec["url"].split("github.com/")[-1].removesuffix(".git")
            provider_roots[source_name] = fetch_archive(
                repo, source_spec["commit"], temp_root / f"provider-{source_name}", args.mirror_prefix,
            )
            fetched[source_name] = str(provider_roots[source_name])
        for path in [baseline, candidate, *provider_roots.values()]:
            if path is None or not path.is_dir():
                raise RuntimeError(f"source tree is missing: {path}")
        profile_reports = []
        for name, config, lock, profile in selected:
            profile_temp = temp_root / re.sub(r"[^A-Za-z0-9._-]", "_", name)
            profile_temp.mkdir()
            base = check_variant(config, lock, profile, baseline, provider_roots, "baseline", profile_temp)
            cand = check_variant(config, lock, profile, candidate, provider_roots, "candidate", profile_temp)
            profile_reports.append(profile_result(name, profile, base, cand))
            shutil.rmtree(profile_temp, ignore_errors=True)
        report = {
            "schema_version": 1, "task": "T22",
            "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "candidate": {"kernel": {"sha": source_identity(candidate)["sha"] or candidate_commit, "expected_commit": locked_commit}, "fetched": fetched},
            "baseline": {"kernel": {"sha": source_identity(baseline)["sha"] or (locked_commit if args.fetch_candidate else None), "expected_commit": locked_commit}},
            "profiles": profile_reports,
            "policy": {"lock_modified": False, "issue_created": False,
                       "patch_failure_means_absorption": False, "config_check_without_dot_config": "not-run"},
        }
        payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.json_out:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            args.json_out.write_text(payload, encoding="utf-8")
        else:
            print(payload, end="")
        if args.markdown_out:
            args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
            args.markdown_out.write_text(markdown(report), encoding="utf-8")
        if args.issue_draft:
            args.issue_draft.parent.mkdir(parents=True, exist_ok=True)
            args.issue_draft.write_text(issue_draft(report), encoding="utf-8")
        hard_failures = [item for item in profile_reports if item["candidate"]["status"] == "failed"]
        incomplete = [item for item in profile_reports if item["candidate"]["status"] == "incomplete"]
        return 1 if hard_failures or incomplete else 0
    finally:
        temporary.cleanup()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, profile_rules.Invalid) as exc:
        print(f"drift-check error: {exc}", file=sys.stderr)
        raise SystemExit(2)
