# Capability and compatibility table

The table separates source/build capability from runtime and publication
acceptance. A warning does not make a profile release-ready; it records a gate
that needs userspace, device or handoff evidence.

| Profile | Base / inheritance | Hook | SUSFS | Container | Source preparation / outstanding gate |
| --- | --- | --- | --- | --- | --- |
| `ace6-minimal-6.6` | Ace6 6.6.142 | none | off | off | T25 AK3 built and checked; this profile has no T26 device run |
| `ace6-resukisu-manual-6.6` | Ace6 + fixed ReSukiSU candidate | Manual | off | off | T25 AK3 built and checked; device/runtime gate remains separate |
| `ace6-resukisu-susfs-inline-6.6` | Ace6 + fixed ReSukiSU/SUSFS candidates | SUSFS Inline | on | off | T25 AK3 built; T26 boot/root/smoke/5-minute soak partial-pass |
| `ace6-droidspaces-standard-6.6` | Ace6 | none | off | standard | T25 AK3 built and checked; container runtime remains untested |
| `ace6-droidspaces-extend-6.6` | inherits standard | none | off | extend | blocked T11 ABI/userspace; experimental |
| `ace6-droidspaces-resukisu-standard-6.6` | inherits standard + ReSukiSU | Manual | off | standard | T25 AK3 built and checked; container runtime remains untested |
| `ace6-droidspaces-resukisu-extend-6.6` | inherits ReSukiSU standard | Manual | off | extend | blocked T11 ABI/userspace; experimental |
| `ace6-rekernel-experimental` | inherits ReSukiSU Manual | Manual | off | off | build-capable; T13/T26 userspace protocol/runtime warning |
| `ace6-main-release-compat-6.6` | ReSukiSU + SUSFS + Droidspaces extend + Re:Kernel | SUSFS Inline | on | extend | build-capable; T20 backing/single-writeback verified, T11/T13 userspace warnings remain |

The fixed ReSukiSU Kconfig presents Manual, Tracepoint and SUSFS Inline as a
choice. M1 explicitly chooses Manual for the root-without-SUSFS candidate and
adds no Tracepoint support promise. Its version-specific Manual Hook rules are
recorded in `docs/manual-hook-rules.md`; Inline cannot silently combine with
another hook mode.

Rejected before preparation: none+SUSFS; conflicting core inputs/profile;
mixed/unknown hook input; ghost_task without containers; KSU module output
without KSU; KPM without a binary version/hash and kernel compatibility record;
debug skip plus publishing; and boot/all packaging without target boot inputs.
SUSFS+Droidspaces is no longer a blanket rejection: only the locked main
composite enables that pairing. Every profile's actual release capability
remains false until the remaining independent runtime, rollback, module and
publication gates are complete. T27 records the current handoff boundary.

T10 has now disabled the legacy `ghost_task` workaround. The exact locked source
trees provide no `oplus_bsp_midas` or fault-scope evidence, and the workaround
would fabricate a `task_struct` at a globally shared PID lookup. The independent
`ghost_task` input remains a deterministic preflight blocker; it is not included
in any profile lock. See `docs/ghost-task-rules.md` and
`docs/execution-t10.md`.

The extend profiles merge standard capabilities and inheritance is tested. The
main composite has a source-locked EVDI Kconfig/Makefile and checked-in EVDI
tree, but the current `create-disp` candidate calls an EVDI power-mode ioctl
absent from that kernel UAPI. EVDI module linking, userspace HCI,
systemd-coredump and Ace6 device/display compatibility therefore remain
warnings. T09's standard patch still does not include EVDI or `ghost_task`; the
main lock adds EVDI separately. See `docs/droidspaces-extend-rules.md`.

T09's standard profile and its ReSukiSU Manual variant have passed locked source
preparation, `olddefconfig`, and NTSYNC object checks. The 42-option kernel
fragment and userspace prerequisites are documented in
`docs/droidspaces-standard-rules.md`. Container startup, isolation and
networking remain T26 runtime checks. `ghost_task` remains excluded from that
claim.

Baseband Guard is an optional legacy feature rather than an M1 profile capability.
T08 fixes its source predicate and verifies the isolated 6.6 objects, but does not
claim a complete kernel build, device behavior, real partition protection, or
release readiness. See `docs/baseband-guard-rules.md` and the T08 evidence.

T12 rebuilt Re:Kernel as a single built-in implementation with formal Kconfig/
Makefile integration and object-level Binder/binder_alloc/signal linkage. The
kernel side is build-capable after T13 fixes, but the profile remains
experimental because it lacks a pinned NoActive userspace counterpart and
runtime evidence; no release claim is made.

ZRAM writeback is a kernel capability plus a device-side hand-off. The separate
`azram-backing` KSU module configures only the backing device; Scene retains
ownership of zram size, algorithm and `swapon`, while ZramWritebackBoost retains
writeback scheduling. The main-profile device evidence verifies the
`/dev/block/sda13` hand-off and one manual writeback trigger. Long-duration
stress, rollback and release acceptance remain separate gates.
