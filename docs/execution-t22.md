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

## Follow-up 2026-09-11 — provider monitoring and baseline identity

The original run above compared the kernel candidate only. The ReSukiSU and
SUSFS sources were fetched to satisfy `link` steps but were never checked
against their own branches, and the five passing profiles each carried a
`locked-baseline-mismatch` next to `no-observed-drift`. Both are corrected in
`scripts/drift.py`.

| Check | Result |
| --- | --- |
| `python3 -m py_compile scripts/drift.py` | passed |
| `python3 -m unittest tests.test_drift -q` | 20/20 passed |
| `python3 scripts/ci.py` | passed; all six gates and the full unit suite |
| provider lookup against the live remotes on 2026-09-11 | kernel/modules/devicetrees `current`; resukisu and susfs `drift` |

The live lookup resolved each source's monitored branch from its descriptive
lock `reference` and compared it with the locked commit:

| Source | Monitored ref | Locked | Observed | Status |
| --- | --- | --- | --- | --- |
| `devicetrees` | `lineage-23.2` | `ebb25e3526ad` | `ebb25e3526ad` | `current` |
| `kernel` | `lineage-23.2` | `cb967c26c2c5` | `cb967c26c2c5` | `current` |
| `modules` | `lineage-23.2` | `7d5d39a539dd` | `7d5d39a539dd` | `current` |
| `resukisu` | `main` | `9d0ff6aea9e2` | `246d3e52e667` | `drift` |
| `susfs` | `gki-android15-6.6` | `937215cb3a1b` | `3f0b811b2e10` | `drift` |

A source branch that moved is advisory. It does not change a lock, does not
invalidate a build, and is not on its own a reason to adopt the newer commit:
the patch set and its consumers have to be re-checked first. The kernel-side locks
still match their upstream tips, so the earlier `no-observed-drift`
classification remains correct for those sources.

Three behaviours were added after the first pass, because a check that reads
nothing must not look like a check that read clean:

- the report carries `source_branch_summary` with the number of sources read,
  unresolved, unmonitored and moved, and the Markdown report states it;
- a lookup is retried once and given 150 seconds instead of 60, since the
  earlier bound was tight enough to time out on a working connection;
- when no source can be read at all, the run warns on stderr and `--ci` exits
  non-zero instead of uploading an empty result as a pass.

A source branch that cannot be resolved stays `unresolved` rather than being
counted as drift or as current. Separately, a baseline or candidate tree that
the caller supplied without a readable commit is now classified
`baseline-identity-unavailable` or `candidate-identity-unavailable`; a tree the
checker fetched itself never carries one, so it is not flagged.

This record does not claim a device or build result, and it does not change
any lock, provider, or Issue state.
