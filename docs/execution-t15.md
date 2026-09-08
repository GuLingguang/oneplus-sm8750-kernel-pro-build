# Ace6 T15 execution record: common build entry

Date: 2026-09-06. At the time of this record, all changes remained local; no
commit, push, release or artifact upload was performed. Later repository cleanup
was committed locally and was not pushed.

## Result

| Area | Result | Boundary |
|---|---|---|
| Input parsing | passed | legacy local flags and Actions-style `ACE6_*` inputs use the same normalizer |
| Source/version lock | passed statically | profile locks use exact source SHAs; optional feature bytes use `manifests/build-features.json` |
| Patch order | passed statically | profile cumulative steps run first, then the selected T14/BBG feature patches; first failure stops |
| Final configuration | implemented | one Python entry owns the T14 switch table and runs `olddefconfig` |
| Image identity check | implemented | compares the actual Image banner with `include/config/kernel.release`; no hard-coded `6.6.139` |
| Debug skip | implemented | requires a fresh work tree and creates a marked dummy Image; it cannot reuse an old Image or claim compilation |
| Manifest | implemented | `build-manifest.json` records config/lock/source/feature/toolchain/config/Image/artifact identities |
| Full Image/package run | not run | this host has clang 22 rather than the locked AOSP Clang 21 and has no `zip`; no packages were installed while unattended |
| Runtime/device | not tested | remains T25/T26 work |

## Common entry

`scripts/build.py` is now the only build implementation. `reproduce.sh` is a
thin local adapter, and the Actions job only installs the environment, maps
workflow inputs into `ACE6_*`, manages ccache and calls the same entry. The
fingerprint path is also shared, so cache identity is derived from the
normalized config, selected lock, kernel commit and locked toolchain digest.

The builder calls the M1 profile preparer in `build` mode. It checks exact
commits and clean external providers, uses a fresh isolated workspace, applies
the locked profile steps, and then records the optional feature patch/source
hashes. The old floating KSU clone and the legacy `02_ksu.patch` “continue on
failure” path are gone. KPM requests stop because no pinned KPM resource is
present; the old `releases/latest` download is not used.

The local/workflow minimal dry-runs produced the same IDs:

```text
The IDs below are the T15 execution-point IDs; later T16/T17 local lock
updates changed the current lock digest while preserving this historical
record:

```text
config_id = b0f963f43d5a37f491044f5bcb0901f3864286e9cc006a3ee728692340504da7
lock_id   = 3fa8668ebb034d08ec283007834695d2efde87f8fb9cfd17efe327b11ee82270
```
```

The representative T14 feature dry-run also verified the locked hashes for
02/03/04 and 06 (`feature_lock_id=7b95e52d5d6d48c06b2ffdb5e1dba9a636a4f995d558242247d0e4bfe18c3b51`).
The T15-point unit suite passed **25/25**; the current suite passes **26/26**;
shell/Python syntax
and `git diff --check` pass. A full build must be resumed only after the locked
toolchain and packaging dependency are available, then the resulting manifest
and Image still need T25/T26 evidence.
