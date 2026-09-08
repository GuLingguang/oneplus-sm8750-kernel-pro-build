# Main Release compatibility profile — implementation record

Date: 2026-09-07. This record covers the local implementation of the agreed
feature combination. It does not authorize a commit, upload, GitHub Release or
device partition write.

## Target

`ace6-main-release-compat-6.6` resolves automatically when the requested core
features are ReSukiSU + SUSFS + Droidspaces `extend` + Re:Kernel. The target
also enables LZ4/zstd, LZ4KD, all zram algorithm backends, zram writeback,
Baseband Guard, CVE compatibility mode, Better network and BBR. KPM is false;
artifact mode is AK3; attribution is `Lingguang` on `kernel-builder`.

The source lock is cumulative and dependency-ordered:

```text
compile fixes
  -> ReSukiSU drivers
  -> SUSFS files and inline integration
  -> Droidspaces standard/NTSYNC
  -> EVDI Kconfig/Makefile and source files
  -> Re:Kernel core and protocol
  -> optional LZ4/zstd, LZ4KD and Baseband Guard patches
  -> final config, Image and AK3 packaging
```

The optional patch chain was checked cumulatively in a disposable exact-source
tree. The legacy monolithic Droidspaces patch is not used because it contains
the rejected `ghost_task` workaround.

## Gate semantics

The build preflight has no hard blocker for the selected main profile. It emits
warnings for EVDI/userspace ABI and virtual HCI/systemd-coredump, Re:Kernel
userspace/protocol, and zram writeback backing-device behavior. The builder
asserts the resulting Kconfig symbols, but these warnings keep
`release_allowed=false`. The build manifest records release intent separately
with `published=false`; the later T20 device follow-up clears only the
backing-device warning, not the userspace or rollback gates.

The GitHub Release job additionally requires the build output
`release_allowed=true`; local execution never publishes.

## Verification performed

- Python syntax checks pass for the profile/build/test entry points.
- The unit suite passes (`27` tests).
- Every checked-in profile lock validates with refreshed local hashes.
- Main-profile dry-run resolves the expected profile, feature lock and four
  optional patches, with no hard blocker and three runtime warnings.
- Local build completed with 30 parallel jobs; the AK3 ZIP passed integrity and
  archive/Image hash checks.
- The running device reports the exact built kernel identity. Kernel-side
  KSU/SUSFS, NTSYNC, EVDI loading, zram algorithms/writeback, networking,
  Baseband Guard and attribution checks passed; EVDI userspace frame flow,
  Droidspaces lifecycle and Re:Kernel protocol remain partial.
- The zram backing module was enabled after an ownership audit. `hybridswap`
  is bound to `/dev/block/sda13`, and one idle writeback command returned
  success; no zram size/algorithm configuration was changed.

## Build result

The local result is a functional-equivalence candidate, not a release:

```text
profile:          ace6-main-release-compat-6.6
kernel release:   6.6.142-4k-gcb967c26c2c5+
Image sha256:     fac576ecbe5ff6554326731e0fdebe855497c92fa794336dcaa53e84673df7d4
AK3:              Kernel-Ace6-Lingguang-ksu35115-20260907.zip
AK3 sha256:       1c890fe6f9d63d2436388c64393cc391c72f689ec3e601523b248ffee312c6da
manifest id:      bf0b856039f34ad681adcd16625a1c333a61a97df701d33d6061bb0885f14ef4
release intent:   requested=true, allowed=false, published=false
```

The Image embedded in the AK3 archive has the same SHA-256 as the verified
worktree Image, and `zip -T` passes. The full build manifest is
`out/main-release-compat-6.6/build-manifest.json`; the artifact remains local.

The remaining acceptance work is runtime/userspace validation and the release
handoff/rollback gates. Device evidence is recorded in
`docs/evidence/main-release-device-20260907.json`; local execution still never
publishes a GitHub Release.
