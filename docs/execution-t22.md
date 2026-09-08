# T22 — cumulative upstream drift check

## Scope and boundary

T22 adds a report-only checker for the locked profiles. It compares a locked
baseline snapshot with a candidate snapshot by applying each profile's ordered
`patch`, `copy`, and supplied `link` steps cumulatively. A failed patch is a
review trigger only; it is not evidence that upstream absorbed the change.

The entry points are `check_upstream.sh` and `scripts/drift.py`. The checker
does not edit locks, source providers, Issues, or release state. Disposable
snapshots and fetched archives are placed under `work/_tmp/` and cleaned after
each profile/run.

## Verification

| Check | Result |
| --- | --- |
| `bash -n check_upstream.sh` | passed |
| `python3 -m py_compile scripts/drift.py scripts/profile.py scripts/build.py` | passed |
| `python3 -m unittest discover -s tests -q` | 26/26 passed |
| all eight selected profiles, locked candidate replay | passed; 5 no-observed-drift, 3 blocked by existing profile rules |
| `ace6-minimal-6.6` wrapper/direct rerun on 2026-09-07 | passed; no-observed-drift |
| JSON/Markdown/Issue-draft output | generated and JSON parsed successfully |

The all-profile candidate and locked baseline both resolve to
`cb967c26c2c5689108fa28d3c3be2aba6ba71f5f`. Therefore this evidence is a
locked-commit replay, not proof that a newer upstream commit has no drift.
The blocked profiles are `ace6-droidspaces-extend-6.6`,
`ace6-droidspaces-resukisu-extend-6.6`, and `ace6-rekernel-experimental`;
their existing profile blockers remain explicit.

## Review rule

When a newer candidate is supplied, inspect the cumulative failure and its
consumer/configuration rule before changing a lock. The generated Issue
file is a draft for human review and is never posted by this checker.
