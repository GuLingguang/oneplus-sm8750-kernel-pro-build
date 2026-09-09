# T27 — local handoff and release-readiness gate

## Result

The local handoff set is assembled, but publication remains blocked. No commit,
upload, GitHub Release, or device partition write was performed by T27.

The first bullets below are the original T27 handoff snapshot. A later
2026-09-07 main-profile follow-up supersedes its old `backing_dev` observation:
`docs/evidence/main-release-device-20260907.json` records the running main
profile, the enabled `azram-backing` hand-off, and the remaining untested
EVDI/Droidspaces/Re:Kernel userspace flows.

A 2026-09-09 T11 follow-up also supersedes the old extend preflight result:
both standalone Droidspaces extend locks now include the standard configuration,
extend integration and EVDI source at `d3b85f3`. They are build-capable
experimental profiles. Display, input, coredump, container and device checks
remain open.

## Artifact audit

- Five non-blocked profiles have build manifests and AK3 zips.
- All five ZIPs passed `zip -T`; each SHA-256 matches its build manifest.
- The current self-authored module sources produced standalone ZIPs under
  `work/_tmp/t27-module-out2/`; `tcp-config v1.1` and `selinux_perf v1.1` were
  installed and boot-verified on the test device. At that original checkpoint,
  `azram-backing v1.2` remained uninstalled because the then-current kernel
  lacked `backing_dev`; the later main-profile follow-up cleared that blocker.
- A follow-up `tcp-config` ZIP under `work/_tmp/t27-module-out3/` fixes only the
  kernel-default display parser; it passed `zip -T` and remains local/uninstalled.
- The three profiles rejected before build remain explicitly blocked: the two
  Droidspaces extend variants and `ace6-rekernel-experimental`.
- `boot.img` and `all` remain blocked by the T18 target-boot-input rule;
  raw `Image` output is development-only.

## Runtime and module boundary

The ReSukiSU + SUSFS Inline AK3 was manually flashed and booted on the target
OnePlus Ace 6. Root ADB, KSU/SUSFS identity, basic hardware smoke checks, and a
five-minute read-only soak passed. This is partial runtime evidence, not a full
feature or rollback table.

The self-authored modules were then handled through separate reversible gates:

- `tcp-config`: old v1.0 was backed up and its unauthenticated `*:8090` listener
  stopped; v1.1 booted successfully, direct apply and real WebUI `cubic/fq`
  click passed. A display-only parser fix is packaged locally but not installed.
- `azram-backing`: old v1.0 was backed up and disabled after reboot in the
  original handoff. The later main-profile follow-up enabled v1.2, bound the
  1 GiB `/dev/block/sda13` backing, preserved Scene/ZramWritebackBoost ownership
  boundaries, and returned `rc=0` for one manual writeback trigger.
- `selinux_perf`: v1.1 booted successfully; disable/enable comparison had zero
  matching AVC records in both 5,000-record samples. Performance benefit remains
  unproven.

## Publication decision

`release_allowed=false` remains the only safe handoff state. Before any public
Release, obtain the missing runtime/module evidence, complete rollback and
longer stability checks, and receive an explicit publication decision. The
artifact hashes and device evidence in T25/T26 are handoff inputs, not an
authorization to upload them.
