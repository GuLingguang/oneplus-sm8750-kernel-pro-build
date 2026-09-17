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


def command(argv, cwd=None, timeout=None):
    try:
        result = subprocess.run(
            [str(item) for item in argv], cwd=str(cwd) if cwd else None,
            text=True, capture_output=True, check=False, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return 124, f"command timed out after {timeout}s: {' '.join(str(item) for item in argv)}"
    return result.returncode, (result.stdout or "") + (result.stderr or "")


def source_identity(path: Path):
    sha = ""
    dirty = None
    if git_root(path) == path.resolve():
        code, output = command(["git", "-C", path, "rev-parse", "HEAD"])
    else:
        code, output = 1, ""
    if code == 0:
        sha = output.strip().splitlines()[-1] if output.strip() else ""
        code, status = command(["git", "-C", path, "status", "--porcelain", "--untracked-files=all"])
        dirty = code != 0 or bool(status.strip())
    return {"path": str(path), "sha": sha or None, "dirty": dirty}


def git_root(path: Path):
    code, output = command(["git", "-C", path, "rev-parse", "--show-toplevel"])
    if code != 0 or not output.strip():
        return None
    root = Path(output.strip()).resolve()
    return root if root == path.resolve() else None


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


PLAIN_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


class BranchMissing(RuntimeError):
    """The remote answered, but it has no branch under the monitored name."""


def tracked_ref(source):
    """Return the branch this checker monitors for one locked source.

    A lock ``reference`` is descriptive text, not a fetch input: builds always
    use the full ``commit``. Monitoring therefore reads only the leading token
    and only when it looks like a plain branch name, so a descriptive value
    such as ``main (candidate from historical run)`` still resolves to ``main``
    while an unparsable one stays unmonitored instead of guessing.
    """
    tokens = str(source.get("reference", "")).split()
    token = tokens[0] if tokens else ""
    return token if token and PLAIN_REF.match(token) else None


def remote_branch(url, branch, mirror_prefix="", timeout=60):
    target = url
    if mirror_prefix and "github.com/" in url:
        target = mirror_prefix.rstrip("/") + "/" + url
    code, output = command(["git", "ls-remote", target, f"refs/heads/{branch}"], timeout=timeout)
    if code != 0:
        raise RuntimeError(output.strip()[-400:] or "git ls-remote failed")
    match = re.search(r"^([0-9a-f]{40})\s+refs/heads/", output, re.MULTILINE)
    if not match:
        raise BranchMissing(f"remote has no branch named: {branch}")
    return match.group(1)


def source_branch_drift(sources, mirror_prefix="", timeout=150, attempts=2):
    """Compare every locked source with the current tip of its monitored branch.

    Provider branches are the inputs most likely to move between runs. This
    reads the remote tip only; it never writes a lock and never turns an
    observed ref into a build input. An unreachable source is reported as
    unresolved rather than treated as drift or as success, and the caller can
    see from the summary how many sources were actually read.
    """
    results = []
    for name in sorted(sources):
        source = sources[name]
        entry = {
            "name": name,
            "url": source.get("url", ""),
            "locked_commit": source.get("commit", ""),
            "tracked_ref": None,
            "observed_commit": None,
        }
        branch = tracked_ref(source)
        if not branch:
            entry.update({
                "status": "unmonitored",
                "detail": "reference is not a plain branch name",
            })
            results.append(entry)
            continue
        entry["tracked_ref"] = branch
        observed = None
        error = None
        for attempt in range(attempts):
            try:
                observed = remote_branch(source.get("url", ""), branch, mirror_prefix, timeout=timeout)
                break
            except BranchMissing as exc:
                error = exc
                break
            except (RuntimeError, OSError) as exc:
                error = exc
        if observed is None:
            # A ref the remote does not have is a naming problem, not a
            # connectivity problem, and the two must not read the same.
            status = "unmonitored" if isinstance(error, BranchMissing) else "unresolved"
            entry.update({"status": status, "detail": str(error)[-400:]})
            results.append(entry)
            continue
        entry["observed_commit"] = observed
        if observed == source.get("commit"):
            entry["status"] = "current"
            entry["detail"] = ""
        else:
            entry["status"] = "drift"
            entry["detail"] = (
                f"locked {source.get('commit')} but {branch} is {observed}"
            )
        results.append(entry)
    return results


def source_branch_summary(branches):
    """Count how many locked sources the checker was actually able to read."""
    return {
        "sources": len(branches),
        "resolved": sum(1 for item in branches if item["status"] in ("current", "drift")),
        "drift": sum(1 for item in branches if item["status"] == "drift"),
        "unresolved": sum(1 for item in branches if item["status"] == "unresolved"),
        "unmonitored": sum(1 for item in branches if item["status"] == "unmonitored"),
    }


def parse_source_args(values):
    result = {}
    for value in values:
        name, separator, path = value.partition("=")
        if not separator or not name or not path:
            raise ValueError(f"source must be NAME=PATH: {value}")
        result[name] = Path(path).expanduser().resolve()
    return result


def collect_source_specs(selected):
    result = {}
    for _, _, lock, _ in selected:
        for name, source in lock["sources"].items():
            if name in result and result[name] != source:
                raise RuntimeError(f"source lock differs between selected profiles: {name}")
            result[name] = source
    return result


def copy_snapshot(source: Path, destination: Path):
    if not source.is_dir():
        raise RuntimeError(f"source tree is missing: {source}")
    if git_root(source) == source.resolve():
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


def apply_patch(kernel: Path, patch: Path, check=False):
    kernel = kernel.resolve()
    try:
        directory = kernel.relative_to(ROOT)
    except ValueError as exc:
        raise RuntimeError(f"snapshot is outside project root: {kernel}") from exc
    mode = "--check" if check else "--verbose"
    return command(
        ["git", "apply", mode, f"--directory={directory}", str(patch)],
        cwd=ROOT,
    )


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
            code, output = apply_patch(kernel, patch, check=True)
            if code != 0:
                records.append(step_record(step, "failed", "patch-apply-failure-needs-review", output))
                return records, "failed"
            code, output = apply_patch(kernel, patch)
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


def check_variant(config, lock, profile, source: Path, source_roots, label, temp_root, identity_expected=True):
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
    # A snapshot materialized from an archive has no git identity. That is a
    # property of the fetch path, not a lock mismatch, so only a readable and
    # genuinely different SHA is reported as identity drift.
    identity_available = bool(identity["sha"])
    if identity_available and identity["sha"] != expected:
        category = ("locked-baseline-mismatch" if label == "baseline"
                    else "candidate-source-identity-drift")
    else:
        category = "none"
    return {
        "source": identity, "expected_kernel_commit": expected,
        "identity_available": identity_available, "identity_expected": identity_expected,
        "status": status, "identity_category": category,
        "steps": steps, "contracts": checks,
    }


def profile_result(name, profile, baseline, candidate, branches=None):
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
    # A tree the caller supplied without a readable commit cannot be checked
    # against the lock at all, which is different from a fetched archive that
    # never carries one.
    if baseline.get("identity_expected") and not baseline.get("identity_available"):
        classes.append("baseline-identity-unavailable")
    if candidate.get("identity_expected") and not candidate.get("identity_available"):
        classes.append("candidate-identity-unavailable")
    for entry in branches or []:
        if entry["status"] == "drift":
            classes.append(f"source-branch-drift:{entry['name']}")
        elif entry["status"] == "unresolved":
            classes.append(f"source-status-unresolved:{entry['name']}")
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
    branches = report.get("source_branches") or []
    if branches:
        summary = report.get("source_branch_summary") or {}
        lines.extend([
            "", "## Locked source branches", "",
            "The monitored branch is advisory. A build always uses the locked commit.", "",
            "Read {} of {} sources; {} unresolved, {} unmonitored, {} moved.".format(
                summary.get("resolved", 0), summary.get("sources", len(branches)),
                summary.get("unresolved", 0), summary.get("unmonitored", 0),
                summary.get("drift", 0)),
            "",
            "| Source | Monitored ref | Locked | Observed | Status |",
            "| --- | --- | --- | --- | --- |",
        ])
        for entry in branches:
            lines.append("| `{}` | `{}` | `{}` | `{}` | {} |".format(
                entry["name"], entry.get("tracked_ref") or "-",
                str(entry.get("locked_commit") or "")[:12],
                str(entry.get("observed_commit") or "")[:12] or "-",
                entry["status"],
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
    drifted = [entry for entry in (report.get("source_branches") or []) if entry["status"] == "drift"]
    unresolved = [entry for entry in (report.get("source_branches") or []) if entry["status"] == "unresolved"]
    if drifted:
        lines.extend(["", "## Provider branches that moved", ""])
        for entry in drifted:
            lines.append(
                f"- `{entry['name']}`: locked `{str(entry['locked_commit'])[:12]}`, "
                f"`{entry['tracked_ref']}` is now `{str(entry['observed_commit'])[:12]}`"
            )
    if unresolved:
        lines.extend(["", "## Provider branches that could not be read", ""])
        for entry in unresolved:
            lines.append(f"- `{entry['name']}`: {entry.get('detail') or 'unresolved'}")
    lines.extend([
        "", "## Required review", "",
        "- classify each failed patch as context/API/type/configuration drift or",
        "  equivalent upstream implementation only after semantic inspection;",
        "- attach the cumulative check log and affected consumer/configuration rule;",
        "- update a lock only in a separate explicitly reviewed change.", "",
    ])
    return "\n".join(lines)


def check_exit_code(profile_reports, summary, ci):
    """Decide the checker's exit status.

    A failure or an incomplete candidate check is a hard failure. Reading no
    source branch at all is also a failure in CI: the scheduled run must not
    upload an empty result as if it were a clean one.
    """
    if any(item["candidate"]["status"] in ("failed", "incomplete") for item in profile_reports):
        return 1
    if ci and summary.get("sources") and not summary.get("resolved"):
        return 1
    return 0


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
    parser.add_argument("--skip-provider-check", action="store_true",
                        help="do not compare locked provider sources with their branch tips")
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
        source_specs = collect_source_specs(selected)
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
            source_spec = source_specs[source_name]
            repo = source_spec["url"].split("github.com/")[-1].removesuffix(".git")
            provider_roots[source_name] = fetch_archive(
                repo, source_spec["commit"], temp_root / f"provider-{source_name}", args.mirror_prefix,
            )
            fetched[source_name] = str(provider_roots[source_name])
        for path in [baseline, candidate, *provider_roots.values()]:
            if path is None or not path.is_dir():
                raise RuntimeError(f"source tree is missing: {path}")
        branches = [] if args.skip_provider_check else source_branch_drift(source_specs, args.mirror_prefix)
        summary = source_branch_summary(branches)
        profile_reports = []
        for name, config, lock, profile in selected:
            profile_temp = temp_root / re.sub(r"[^A-Za-z0-9._-]", "_", name)
            profile_temp.mkdir()
            base = check_variant(config, lock, profile, baseline, provider_roots, "baseline", profile_temp,
                                 identity_expected=bool(args.baseline_kernel))
            cand = check_variant(config, lock, profile, candidate, provider_roots, "candidate", profile_temp,
                                 identity_expected=not args.fetch_candidate)
            used = set(lock["sources"])
            relevant = [entry for entry in branches if entry["name"] in used]
            profile_reports.append(profile_result(name, profile, base, cand, relevant))
            shutil.rmtree(profile_temp, ignore_errors=True)
        report = {
            "schema_version": 1, "task": "T22",
            "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "candidate": {"kernel": {"sha": source_identity(candidate)["sha"] or candidate_commit, "expected_commit": locked_commit}, "fetched": fetched},
            "baseline": {"kernel": {"sha": source_identity(baseline)["sha"] or (locked_commit if args.fetch_candidate else None), "expected_commit": locked_commit}},
            "source_branches": branches, "source_branch_summary": summary,
            "profiles": profile_reports,
            "policy": {"lock_modified": False, "issue_created": False,
                       "patch_failure_means_absorption": False, "config_check_without_dot_config": "not-run",
                       "provider_branch_is_build_input": False},
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
        if branches and summary["resolved"] == 0:
            # Reading nothing must not look like reading clean.
            print("drift-check warning: no locked source could be read; "
                  f"{summary['unresolved']} unresolved, {summary['unmonitored']} unmonitored", file=sys.stderr)
        return check_exit_code(profile_reports, summary, args.ci)
    finally:
        temporary.cleanup()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, profile_rules.Invalid) as exc:
        print(f"drift-check error: {exc}", file=sys.stderr)
        raise SystemExit(2)
