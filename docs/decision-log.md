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

## 2026-09-11 — Provider drift monitoring and baseline identity

1. Monitor every locked source against the current tip of its branch. The
   kernel side was already compared through the candidate snapshot, but the
   ReSukiSU and SUSFS providers were only fetched to satisfy `link` steps.
   Those two are the inputs most likely to move, so `scripts/drift.py` now
   resolves each locked source's branch head and records `current`, `drift`,
   `unresolved`, or `unmonitored`.
2. Read only the leading token of a lock `reference`. Those fields are
   descriptive (`main (candidate from historical run; not floating)`,
   `gki-android15-6.6 / v2.3.0`), and a build still uses the full commit only.
   A reference that is not a plain branch name stays `unmonitored` instead of
   being guessed, and the resolved branch is printed so the parse is auditable.
3. Treat an unreadable remote as `unresolved`. A network failure is neither
   drift nor success, so it is reported and does not fail the run. The
   `git ls-remote` lookup carries a bounded timeout so an offline check cannot
   hang. `--skip-provider-check` restores the previous behaviour.
4. Stop reporting a fetched archive baseline as `locked-baseline-mismatch`. A
   snapshot materialized from an archive has no git identity, and comparing
   that absent SHA with the locked commit produced a mismatch on every profile
   while the same row also said `no-observed-drift`. Only a readable and
   genuinely different SHA is identity drift now; `identity_available` records
   whether the identity could be read at all.

## 2026-09-11 — CI/local comparison and the pahole gap

1. Run the CI/local comparison on one lock instead of leaving it open. The
   earlier local artifacts were built before the 2026-09-09 lock refresh, so
   their `lock_id` no longer matches any checked-in lock and they cannot serve
   as the local side of a same-lock comparison. `ace6-minimal-6.6` was rebuilt
   from the current lock and compared with Run `34310782005`.
2. Record the finding as a host-input gap, not as a code defect. Both builds
   used one lock, one profile and one feature lock, and their embedded
   configurations are identical across all 8,757 lines except
   `CONFIG_PAHOLE_VERSION` (`131` locally, `125` on the runner). That is the
   host pahole package. The locks do not pin it: their `build_environment`
   limitations name apt dependencies and mkbootimg only.
3. Keep `byte_identical_build=false`. Two inputs differ between the two builds,
   the pahole version and the build stamp, and the Image sizes differ by 65,536
   bytes. That gap is reported as observed rather than attributed to either
   input on its own, since the comparison does not separate them.
4. Do not treat `ccache_debug` or the runner locale as build inputs. The first
   changes only `config_id`, the second only the wording of patch logs. Both
   appeared in the comparison and neither reaches the kernel.
5. Do not reuse a pre-refresh artifact for validation. Editing a hashed local
   input such as `scripts/build.py` changes every lock that lists it, and the
   artifacts built from the earlier locks describe a configuration that is no
   longer checked in.

## 2026-09-11 — Deterministic build stamp

1. Derive the embedded build stamp instead of taking the wall clock. `init/Makefile`
   writes `KBUILD_BUILD_TIMESTAMP` into `UTS_VERSION` verbatim and falls back to
   `date` when it is unset, which made the Image depend on the build moment and
   on the host timezone. An empty `build_time` now resolves to the locked kernel
   commit's committer date in UTC; an explicit value is still used unchanged.
2. Keep the value tied to a locked input rather than to a fixed constant. A
   hard-coded date would need editing whenever the kernel lock moves; the commit
   date follows the lock automatically and stays meaningful in `uname -a`.
3. Record the resolved stamp and its origin. The manifest carries
   `build.build_timestamp` and `build.build_timestamp_source`
   (`explicit` or `locked-commit-date`), so a reader can tell where the value
   came from without re-running the build.
4. Record the host pahole version as `toolchain.pahole`. It changes the
   generated BTF and therefore the Image bytes, and it is the one remaining
   unlocked input that separates this host from the runner. It is recorded, not
   asserted: pinning it would break either the host or the runner until both
   use one version.
5. Refresh the `scripts/build.py` digest in all nine locks. The locks hash that
   file, so the change invalidated them, and artifacts built from the previous
   lock IDs no longer describe a checked-in configuration. The earlier CI
   artifacts stay valid for device testing; they simply do not match a future
   lock.
6. Stamp the packaged entries from the same locked commit date and run `zip`
   with `TZ=UTC`. Two builds from one lock still produced different archives
   because `zip` records each entry's modification time and because the DOS
   fields follow the local timezone. Two packaging runs over one Image now
   produce the same file, so the archive no longer adds a variable of its own.
   The date inside the artifact file name is taken from the same locked commit,
   so `artifact_name` and `manifest_id` follow the lock rather than the build
   day.
7. Leave the module signing key alone. `CONFIG_MODULE_SIG=y` with the default
   `certs/signing_key.pem` makes the kernel generate a random RSA key and a
   time-stamped self-signed certificate on every build, which is the last input
   that separates two builds from one lock. Supplying a fixed key is a
   key-management decision for the repository owner and is not taken here.

## 2026-09-11 — Fixed module signing key and artifact date

1. Use the checked-in `keys/module-signing.pem` instead of a generated key.
   `CONFIG_MODULE_SIG=y` with the default `certs/signing_key.pem` made the
   kernel create a random RSA key and a certificate dated at generation time on
   every build, which was the last input separating two builds from one lock.
   `certs/Makefile` only generates a key when `CONFIG_MODULE_SIG_KEY` is exactly
   `certs/signing_key.pem`, so the build now points that option at the
   checked-in file and the embedded certificate stops moving.
2. Treat that key as a build input, not a secret. It signs nothing here: no
   loadable module is built, `CONFIG_MODULE_SIG_ALL` is unset, and
   `CONFIG_MODULE_SIG_FORCE` is unset, so signature enforcement is off and the
   key is not a trust anchor. What it buys is a reproducible Image. If
   enforcement is ever turned on, this key is public and must be replaced
   first.
3. Record it in each lock's `local_files`, so a missing or edited key fails
   validation instead of silently changing every artifact.
4. Take the date in artifact names from the locked commit as well. It was the
   last wall-clock value reaching `artifact_name` and `manifest_id`; the
   archive bytes were already fixed. A build now produces the same file name
   for as long as the lock does not move, and the workflow's Release tag still
   carries the run timestamp where a per-run identifier is wanted.
5. Normalise the build path with `-ffile-prefix-map`. Debug info recorded the
   absolute build directory, and `--build-id=sha1` hashes the whole vmlinux
   including debug sections, so building in a different directory changed the
   Image even when every other input matched. This also makes a local build
   comparable with a CI one, which lives under a different path. clang applies
   the last matching map, so the narrower work path is listed after the
   repository path.
6. Leave the remaining 60 bytes open rather than papering over them. After the
   three changes above the Image differs only in its three build-id notes,
   because the DWARF still varies somewhere that the prefix map does not reach.
   Removing or pinning the build id would close it, and that trades a debugging
   aid for a byte count, so it is recorded as a decision to take rather than
   taken here.

## 2026-09-16 — Byte-identical builds

This entry supersedes item 6 of the 2026-09-11 note, which left the last 60
bytes open.

1. Cover every flag channel with the prefix map. Two channels were still
   missing, and each one held the absolute build path in a line table:
   `KAFLAGS`, because `.S` files build from `KBUILD_AFLAGS` rather than
   `KBUILD_CFLAGS`; and `KCPPFLAGS_COMPAT`, because the 32-bit compat vDSO
   Makefile assembles its own `VDSO_CFLAGS`/`VDSO_AFLAGS` and documents that
   variable as the place for user-supplied flags.
2. Fix the cause instead of the symptom. The remaining difference was two
   20-byte GNU build ids, one for the vmlinux and one for the embedded compat
   vDSO. Pinning or dropping the build id would have closed the byte count in
   one line, but it trades away a debugging aid. Making the debug information
   deterministic removes the difference and keeps the build id meaningful.
3. Record the result. Two builds of `ace6-minimal-6.6` from one lock now produce
   the same Image (`7e4dd0bb…`) and the same AK3 (`ad27c54f…`); only
   `build.started_utc` and the `manifest_id` derived from it differ. Evidence is
   in `docs/evidence/t25-byte-identical-20260916.json`.
4. Keep the pahole caveat. These two builds share a host, so they share a pahole
   version. A lock is a byte-identical claim only across hosts whose pahole
   versions match, since pahole changes `CONFIG_PAHOLE_VERSION` and the
   generated BTF.
5. Note the measurement trap for anyone repeating this. With
   `CONFIG_DEBUG_INFO_COMPRESSED_ZSTD=y` the compressed sections avalanche, so
   `cmp` on the compressed vmlinux reported 38 million differing bytes while the
   real difference was one string. Decompress first, and compare section hashes
   rather than byte counts.
