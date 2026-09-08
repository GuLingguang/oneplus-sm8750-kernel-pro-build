# Maintaining M1 profiles

Start with `docs/execution-m1.md`, `docs/execution-t15.md`, then
`docs/profile-rules.md`. The source-preparation entry is
`python3 scripts/profile.py`; the common build entry is
`python3 scripts/build.py` (with `reproduce.sh` as its local adapter). Do not
use an old historical run as validation of the new profiles.

Before opening a change, run `python3 scripts/ci.py`. This is the network-free
repository gate: it checks profile/lock pairs, build dry-run identities, shell
syntax, workflow action pinning, generated-file placement, whitespace, and the
unit tests. The WebUI bundle is checked separately by `.github/workflows/ci.yml`
with its `package-lock.json` dependency graph.

To update a source, inspect the exact commit and update the lock in a reviewable
change. `reference` is only a descriptive branch/tag label. Never resolve it
implicitly during a build and never fall back after a fetch failure. Verify the
selected integration's cumulative patches and rules before removing blockers.

When editing profile inheritance, refresh its canonical `profile_sha256` and
every affected child lock. When editing a hashed local input, refresh the
corresponding `local_files` entry only after reviewing the change. Run
`python3 -m unittest discover -s tests -v` and the relevant real-source preparation
case. Store the actual manifest/lock IDs and results in the execution record.

The original input plan and dossier remain historical source documents. The
execution record tracks completion/partial/blocked states without rewriting those
documents or implying later tasks have run. Feature tasks require their own
configuration, build and runtime evidence before status is promoted.

Use `check_upstream.sh` for the T22 cumulative drift report. It applies the
locked steps to disposable snapshots, writes JSON/Markdown plus an Issue draft,
and never edits locks or GitHub Issues. The T23 scheduled workflow has only
`contents: read` permission and uploads the report as an artifact; it does not
create, comment on, or close an Issue. Local snapshots and default reports live
under `work/_tmp/` so a large check does not fill system `/tmp`. M1 only pins
its Actions references; it does not dispatch the workflow or change Issue #3.
The T15 build entry creates local manifests and artifacts, but release
publication, full feature acceptance and runtime evidence remain T18/T25–T27.
