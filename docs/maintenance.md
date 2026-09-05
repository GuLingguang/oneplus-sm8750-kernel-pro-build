# Maintaining M1 profiles

Start with `docs/execution-m1.md`, then `docs/profile-contract.md`. The new entry
is `python3 scripts/profile.py`; legacy build/reproduce/drift scripts have not
been migrated. Do not use their green status as validation of the new profiles.

To update a source, inspect the exact commit and update the lock in a reviewable
change. `reference` is only a descriptive branch/tag label. Never resolve it
implicitly during a build and never fall back after a fetch failure. Verify the
selected integration's cumulative patches and contract before removing blockers.

When editing profile inheritance, refresh its canonical `profile_sha256` and
every affected child lock. When editing a hashed local input, refresh the
corresponding `local_files` entry only after reviewing the change. Run
`python3 -m unittest discover -s tests -v` and the relevant real-source preparation
case. Store the actual manifest/lock IDs and results in the execution record.

The original input plan and dossier remain historical source documents. The
execution record tracks completion/partial/blocked states without rewriting those
documents or implying later tasks have run. Feature tasks require their own
configuration, build and runtime evidence before status is promoted.

Do not invoke the old scheduled drift workflow to test this framework: it can
create an Issue on failure. T22/T23 will replace its cumulative checking/reporting
behavior. M1 only pins its Actions references; it does not dispatch it or change
Issue #3. Build and release operations are not implemented in the M1 preparer.
