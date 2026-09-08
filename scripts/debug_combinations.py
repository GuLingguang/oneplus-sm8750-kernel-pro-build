#!/usr/bin/env python3
"""Check every feature input combination without downloading or compiling."""
from __future__ import annotations

import argparse
from collections import Counter
import itertools
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import profile as profile_rules  # noqa: E402


FEATURE_FIELDS = tuple(
    field
    for field, spec in profile_rules.read_json(ROOT / "schemas/input-fields.json").items()
    if spec["layer"] == "features"
)


def choices(spec):
    if spec["type"] == "boolean":
        return (False, True)
    return tuple(spec["enum"])


def feature_inputs():
    fields = profile_rules.read_json(ROOT / "schemas/input-fields.json")
    values = [choices(fields[field]) for field in FEATURE_FIELDS]
    for combination in itertools.product(*values):
        yield dict(zip(FEATURE_FIELDS, combination))


def profile_plans():
    plans = []
    for path in sorted((ROOT / "profiles").glob("*/profile.json")):
        name = path.parent.name
        config, selected = profile_rules.normalize({}, name)
        lock = profile_rules.read_json(ROOT / "manifests/locks" / f"{name}.lock.json")
        profile_rules.validate_lock(lock, config, selected)
        report = profile_rules.preflight(config, selected, lock, phase="build")
        plans.append({
            "profile": name,
            "status": "blocked" if report["blockers"] else "ready",
            "blockers": report["blockers"],
            "warnings": report["warnings"],
        })
    return plans


def check_combination(raw, locks):
    try:
        config, selected = profile_rules.normalize(raw)
        lock = locks[selected["name"]]
        report = profile_rules.preflight(config, selected, lock, phase="build")
        status = "blocked" if report["blockers"] else "ready"
        return {
            "status": status,
            "profile": selected["name"],
            "blockers": report["blockers"],
        }
    except profile_rules.Invalid as exc:
        return {"status": "rejected", "error": str(exc)}


def build_report():
    plans = profile_plans()
    locks = {}
    for item in plans:
        locks[item["profile"]] = profile_rules.read_json(
            ROOT / "manifests/locks" / f"{item['profile']}.lock.json"
        )

    status_counts = Counter()
    profile_counts = Counter()
    rejection_counts = Counter()
    blocker_counts = Counter()
    total = 0
    for raw in feature_inputs():
        result = check_combination(raw, locks)
        total += 1
        status_counts[result["status"]] += 1
        if result.get("profile"):
            profile_counts[result["profile"]] += 1
        if result["status"] == "rejected":
            rejection_counts[result["error"]] += 1
        for blocker in result.get("blockers", []):
            blocker_counts[blocker] += 1

    return {
        "schema_version": 1,
        "feature_fields": list(FEATURE_FIELDS),
        "total_inputs": total,
        "status_counts": dict(sorted(status_counts.items())),
        "profile_counts": dict(sorted(profile_counts.items())),
        "rejection_counts": dict(rejection_counts.most_common()),
        "blocker_counts": dict(blocker_counts.most_common()),
        "profiles": plans,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = build_report()
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"feature fields: {len(report['feature_fields'])}")
    print(f"input combinations: {report['total_inputs']}")
    for status, count in report["status_counts"].items():
        print(f"{status}: {count}")
    for item in report["profiles"]:
        print(f"profile {item['profile']}: {item['status']}")
    if args.json_out:
        print(f"report: {args.json_out}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, profile_rules.Invalid) as exc:
        print(f"debug combination check failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
