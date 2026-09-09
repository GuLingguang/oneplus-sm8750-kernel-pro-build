# Decision log

## 2026-09-05 — M1 implementation begins

1. User instruction to begin the supplied plan authorizes the first T01–T05
   implementation batch; the older audit-only restriction is historical.
   Issue #3 comments/closure, merging and publishing remain outside this batch.
2. Preserve `c303fae1f308cd8c0a01b22f28b5bd34de6ab21a` as a legacy checkpoint.
   Work is isolated from the existing scratch trees that contain local changes.
3. Correct the ambiguity between workflow defaults (none/SUSFS off) and run
   33852164627 (explicit ReSukiSU/SUSFS on). Historical success covers only that
   run's enabled branch and does not establish runtime correctness.
4. Choose stdlib Python and JSON for the common normalization/preparation entry.
   No pip install, downloaded setup shell script or new floating dependency is
   needed for M1. The existing build entry points remain until T15.
5. Keep ReSukiSU's historical exact source as a candidate instead of silently
   following its advanced main branch. The official SUSFS source is pinned at
   v2.3.0; compatibility and replacement patch order remain gated by T06/T07.
6. Provide an explicit Manual candidate for KSU without SUSFS. Do not promise
   Tracepoint support. Containers default to no SUSFS; extend inherits standard.
7. Treat vendored feature content hashes as byte provenance only. Observed latest
   upstream commits are recorded as candidates, not invented origins of the old
   patches. Build environment/resource gaps keep T03 partially complete.
8. Source-preparation success, build success and runtime acceptance use separate
   statuses. No M1 output is a flashable kernel or a release recommendation.

## 2026-09-06 — T07 Manual Hook source rules

1. Use the locked ReSukiSU Manual Hook checker as the source of truth for the
   6.6 candidate. The manual profile applies the common compile fix, links the
   complete ReSukiSU `kernel/` tree, adds the Ace6 driver build entries, and then
   applies the version-specific Manual Hook patch.
2. Keep the three 6.6-compatible automatic options selectable. When an automatic
   setuid, init-rc, or input hook is disabled, the corresponding manual call in
   the patch is required; when it is enabled, ReSukiSU's LSM/input path owns that
   hook and the manual call is compiled out.
3. Record static symbol visibility changes for `CONFIG_KALLSYMS_ALL=n` as part
   of the source rules. This source-level result does not imply a successful build or
   runtime behavior.

## 2026-09-05 — T06 SUSFS Inline source preparation

1. Keep the complete locked ReSukiSU `kernel/` tree as a relative source link;
   do not copy or overlay a second KSU adapter into the kernel tree.
2. Use the official SUSFS `gki-android15-6.6` files and patch as the upstream
   input, adapting only the target tree's `vma_data_pages()` context.
3. Treat the `struct filename **` faccessat/stat signatures, filename ownership,
   thread flags and zygote-next mount lookup as one cross-tree interface. The
   inactive non-SUSFS/manual branch's `const char __user **` signatures are not
   selected by this profile.
4. Record source preparation and static interface evidence separately from
   compilation, olddefconfig, runtime mount hiding and publication. T07 remains
   the next gate for the remaining signature/guard/consumer checks.

## 2026-09-06 — T08 Baseband Guard source rules

1. Pin the BBG source identity to `cctv18/Baseband-guard` commit
   `a5b57f15d6b597a1bd157c42330fe80020b1d628`; a mirror may transport the bytes
   but may not replace that identity.
2. Make the dentry predicate safe for NULL/ERR/negative/inode-less inputs and
   return a real protection decision for non-allowlisted block devices. Resolve
   only absolute symlinks, release `get_link()` callbacks and `kern_path()` paths,
   and preserve the allowlist/trusted-process boundary.
3. Stop the vendored Makefile from probing the parent kernel Git repository or
   fetching during a build. BBG object compilation and a disposable decision
   model pass; complete kernel, runtime and destructive partition tests remain
   open.

## 2026-09-06 — T09 Droidspaces standard source rules

1. Keep Droidspaces standard separate from the legacy `05_droidspaces.patch`:
   its EVDI and global `ghost_task` changes are not standard prerequisites and
   remain T11/T10 work.
2. Add only NTSYNC and the 6.6 Android-kABI SYSVIPC layout adaptation to the
   standard cumulative patch. Keep the 42 required kernel settings in a
   profile-specific fragment instead of mutating the historical final config.
3. Use the target tree's `CONFIG_NF_CT_NETLINK` symbol; the upstream guide's
   `CONFIG_NF_CONNTRACK_NETLINK` name does not exist in this 6.6 Kconfig.
4. Wire the ReSukiSU standard child to the same fragment/patch and T07 Manual
   Hook sequence, with `CONFIG_KSU_SUSFS=n`. The validator rejects SUSFS plus
   Droidspaces before preparation, and `ghost_task=true` remains independently
   blocked by T10.
5. Mark source preparation and static configuration/object checks complete, but
   keep full kernel build, container runtime, device, networking and release
   claims open. The exact Droidspaces candidate remains recorded in the existing
   upstream-candidate manifest; a newer mirror checkout is not adopted.

## 2026-09-06 — T10 ghost_task vendor workaround

1. Do not integrate the legacy `kernel/pid.c` ghost-task hunk into any Ace6,
   Droidspaces or ReSukiSU profile. The exact locked kernel/modules sources do
   not contain `oplus_bsp_midas`, `ghost_task`, a device/ROM scope or an
   original fault trace tying the workaround to this target.
2. Reject the semantic rule even though the isolated `kernel/pid.o` object
   compiles. `find_task_by_vpid()` is globally exported and consumed by 15
   other kernel source files; a `memcpy(init_task)` static object cannot prove
   valid PID, RCU, list, reference-count, signal, namespace or task lifetime
   invariants.
3. Keep `ghost_task` as an explicit independent preflight gate only. Enabled
   input remains `prepare_allowed=false`, affected vendor/device combinations
   remain experimental/blocked, and no generic container or release claim is
   made. Reconsideration requires a reproducible vendor-specific interface and
   a narrow lifetime-safe implementation.

## 2026-09-06 — T11 Droidspaces extend rules

1. Preserve both extend profile identities and verify inheritance from their
   standard bases. Extend keeps the standard feature set and adds no SUSFS or
   implicit hook mode; it remains experimental and blocked.
2. Identify the checked-in EVDI source as an exact match for
   `Linux-on-droid/lindroid-drm-loopback@f15bc3ee6e9a90e85e70ef3da057f027c68cbefd`.
   The isolated `evdi.o` object compiles against the locked 6.6 target, but
   module modpost cannot be accepted without the target kernel's Module.symvers.
3. Do not operationally lock the current userspace set yet. The captured
   `create-disp` candidate calls `DRM_EVDI_SET_POWER_MODE (0x0f)` while the
   candidate kernel UAPI has no such ioctl; HCI requires Android framework
   permission/uinput/device policy, and systemd-coredump requires a pinned
   systemd/rootfs definition. These are explicit blockers, not inferred kernel
   capabilities.
4. Do not request a device test for this unresolved ABI. After a compatible
   userspace/ROM/rootfs set and full module build are fixed, T26 must test EVDI
   display/DPMS, virtual input, container lifecycle and coredump recovery on a
   named Ace6 device.

## 2026-09-06 — T12 Re:Kernel formal integration

1. Keep the historical `patches/split/09_rekernel.patch` unchanged for
   comparison, but do not use its header-only implementation. The operational
   experimental lock now points to `patches/integration/ace6-rekernel-6.6.patch`.
2. Put all Re:Kernel state and implementation in one built-in
   `drivers/rekernel/rekernel.c`; keep the header to declarations and interface
   constants. Add `CONFIG_REKERNEL`, the driver Makefile and the `drivers/`
   source/obj wiring so the Binder, binder allocator and signal callers resolve
   one shared state.
3. Guard lazy initialization with one mutex. If netlink or either proc object
   fails, release every resource acquired by that attempt and return to a
   retryable down state. This is static/object-verified, not a concurrent
   runtime stress result.
4. Keep the profile experimental and blocked on T13. The signal sender/target
   semantics, Binder allocator task reference and NoActive protocol are not
   silently treated as fixed by the T12 structural rebuild.

## 2026-09-06 — T13 Re:Kernel semantics and protocol

1. Use `p` as the signal freeze target and `current` as the killer; emit
   `killer_*` from `current` and `dst_*` from `p`. The old reversed fields are
   not retained in the operational T13 patch.
2. Replace the Binder allocator's RCU-only lookup with
   `find_get_task_by_vpid()` and pair it with `put_task_struct()` after event
   formatting. The event path must not dereference an unreferenced task after
   unlocking RCU.
3. Lock `ace6-rekernel-kv/v1`: netlink unit `22..25`, unit discovery through
   `/proc/rekernel/<unit>`, userspace port `100`, kernel-to-userspace unicast,
   comma-separated key/value payloads terminated by `;`, and a 127-byte payload
   limit. Required-length checks reject truncation.
4. No matching NoActive receiver/version exists in the workspace. Keep the
   kernel-side interface and fixes in the experimental lock, but retain the
   T13/T26 userspace/runtime blocker and do not request a device test yet.

## 2026-09-06 — T14 compression and feature switches

1. Pin the audited upstream identities to LZ4 `v1.10.0` commit
   `ebb370ca83af193212df4dcbadcc5d87bc0de2f0`, zstd `v1.5.7` commit
   `f8745da6ff1ad1e7bab384bd1f9d742439278e99`, and the observed
   `SukiSU_patch` candidate `547ae94bcaec53d030398f857950c64662043a5d`.
   The local bytes remain authoritative; LZ4/zstd kernel adaptations are not
   misreported as byte-identical upstream copies.
2. Treat `lz4_zstd` as a replacement-source toggle. Do not disable native
   LZ4/zstd CONFIGs when false if other selected kernel users require them;
   explicitly document that dependency rather than silently claiming the
   algorithms are absent.
3. Make LZ4KD false deterministic: disable its crypto/library symbols and
   select the valid LZO-RLE fallback. Make the true branch select LZ4KD as
   the Kconfig default. Explicitly close BBR, Better network, writeback,
   tracking, LZ4HC and 842 settings when their inputs are false.
4. Accept T14 as static/source/config complete and object-only. The zram
   backend list and compression/decompression objects compile, but no full
   Image, booted crypto round trip, writeback backing device, BBR runtime or
   device result is inferred.

## 2026-09-06 — T15 common build entry

1. Make `scripts/build.py` the single implementation for local and Actions
   builds. `reproduce.sh` and the workflow are adapters for flags/environment,
   host setup and ccache; neither owns a second patch/config/Image path.
2. Resolve a selected profile and exact lock before source preparation. The
   profile lock controls cumulative integration steps, while
   `manifests/build-features.json` pins optional feature patch/extra bytes and
   their observed upstream source identities.
3. Stop on KSU or feature patch failure. Do not retry/continue after the old
   `02_ksu.patch` check, and do not use a floating KPM `releases/latest`
   download. KPM remains rejected until T17 supplies a compatible pinned
   resource.
4. Derive `CONFIG_LOCALVERSION` from the locked kernel commit when no suffix
   is supplied, and validate the Image's actual `Linux version` banner against
   `include/config/kernel.release`. A debug skip creates a fresh dummy Image
   and is recorded as skipped, never as a successful compile.
5. Keep the full Image/package and runtime claims open. The current host lacks
   the locked AOSP Clang 21 archive and `zip`; no unattended installation was
   attempted, and no real-device test is part of T15.

## 2026-09-06 — T16 identity and filename rules

1. Keep display identity literal and separate from filename components. User,
   host, suffix, build time and tag are preserved in normalized config and the
   build manifest; filenames use an explicit safe ASCII mapping.
2. Use Python arguments/environment and callable replacement functions for
   Kbuild/AK3 text. Backslashes, quotes, ampersands, slashes and command-like
   text therefore remain data and cannot become shell or replacement syntax.
3. Make attribution-off deterministic: clear Kbuild user/host and KSU
   `REPO_NAME`, use `Ace6` in the filename mapping, and omit the KSU marker when
   `ksu_type=none`. A selected custom suffix is included in the package name;
   the locked commit fallback remains the kernel localversion source.
4. Pass Release metadata through environment variables in Actions. The build
   job still remains behind the release/build gates; no publication was made.

## 2026-09-06 — T17 KPM/KPatch-Next resource boundary

1. Pin the KPatch-Next source audit to `456744b29efb9989445463ab29e368fa59a103c4`
   (0.13.5 revision 2). Its current image magic is `KP2026`, introduced by
   `cc19c5ee72b05d5c3a2cfcf0fd3c3079ca81a5e4`.
2. Reject the available `sukisu-patch` KPM bundle as a substitute: its
   `kpm/kpimg` is `KP1158`, and the companion tools are prebuilt from the
   same older bundle. Do not turn an observed binary into a lock merely from
   its filename or version-like strings.
3. Keep `resources.kpm` null in every profile. The current builder must stop
   when KPM is requested until a compatible binary/resource hash and kernel
   compatibility record are established.
4. Stop T17 in the unattended environment because the exact target compiler,
   Android NDK and packaging `zip` are missing. No privilege escalation,
   network download, old-binary reuse, full build, or device claim was made.

## 2026-09-07 — Main Release feature composition and local build gate

1. Treat the recorded Release feature list as a functional-equivalence target:
   ReSukiSU, SUSFS Inline, LZ4/zstd, LZ4KD, all zram algorithms, zram
   writeback, Droidspaces extend, Baseband Guard, CVE compatibility, Better
   network, BBR and Re:Kernel; KPM remains disabled.
2. Permit feature composition unless a concrete source/config conflict exists.
   The exact main profile is `ace6-main-release-compat-6.6`; its lock applies
   standard Droidspaces, a separate EVDI integration/source copy and Re:Kernel
   after the SUSFS chain. It never applies the legacy `ghost_task` workaround.
3. Treat EVDI/userspace, Re:Kernel userspace/protocol and zram backing-device
   checks as warnings for local build capability. They keep
   `release_allowed=false` until runtime, rollback and handoff evidence exist.
4. Record `release_enable=true` as requested intent in the build manifest, but
   keep `published=false`. The Actions Release job requires the explicit
   `release_allowed` output; this implementation performs no upload or publish.
5. Keep all intermediate and ccache debug files under the selected project
   workspace (`work/_tmp`), and use 30 parallel jobs for the local full build.

## 2026-09-07 — Main-profile device follow-up and repository handoff

1. The main-profile device check cleared the T20 backing-interface warning:
   `azram-backing v1.2` binds the 1 GiB `/dev/block/sda13` partition through
   writable zram `backing_dev`; Scene remains responsible for zram size,
   compressor and swapon, while ZramWritebackBoost remains responsible for
   writeback scheduling.
2. A manual `echo idle > /sys/block/zram0/writeback` returned zero and the
   device reported nonzero backing statistics. This is a one-shot functional
   check, not a long stress or rollback claim.
3. The main profile still does not become release-ready: EVDI frame/userspace,
   Droidspaces container/display lifecycle, and Re:Kernel userspace protocol
   were not exercised. Publication, commit and upload remain disabled.
4. Repository cleanup keeps all intermediates under `work/`, removes tracked
   WebUI dependencies from the source tree, and adds the network-free
   `scripts/ci.py` gate plus the WebUI build job.

## 2026-09-09 — Droidspaces extend build adaptation

1. Pin `Linux-on-droid/lindroid-drm-loopback@d3b85f3251beae4bc8481538f37d13b7f30abde0`
   and update the 14 checked-in EVDI files. This revision contains the
   `DRM_EVDI_SET_POWER_MODE` UAPI and handler used by the selected `create-disp`
   candidate.
2. Add the standard Droidspaces patch, extend patch and all EVDI copy steps to
   both standalone extend locks. Their lock records use the same EVDI source
   and per-file hashes as the main profile.
3. Apply the standard 6.6 configuration fragment to both `standard` and
   `extend` builds. The extend path must retain the standard namespace,
   cgroup, filesystem, networking and NTSYNC settings.
4. Move the remaining HCI, systemd-coredump, ROM/framework and device checks
   to runtime warnings. Both profiles completed local full Image/AK3 builds;
   they remain experimental with `release_allowed=false` until device tests
   and the userspace path are checked.
