# OnePlus Ace 6 Kernel Builder

> **English** | [中文（简体）](README_zh.md)

> OnePlus Ace 6 (ktm, SM8750) custom kernel builder — configurable GitHub Actions build with ReSukiSU + SUSFS + Droidspaces + Re:Kernel support, verified on Project Infinity X (Android 16).

![GitHub Release](https://img.shields.io/github/v/release/GuLingguang/oneplus-sm8750-kernel-pro-build)
![GitHub License](https://img.shields.io/github/license/GuLingguang/oneplus-sm8750-kernel-pro-build)
![Build](https://img.shields.io/github/actions/workflow/status/GuLingguang/oneplus-sm8750-kernel-pro-build/build.yml?label=build&logo=githubactions)
![Drift check](https://img.shields.io/github/actions/workflow/status/GuLingguang/oneplus-sm8750-kernel-pro-build/upstream-check.yml?label=drift%20check)
![Clean ccache](https://img.shields.io/github/actions/workflow/status/GuLingguang/oneplus-sm8750-kernel-pro-build/clean-ccache.yml?label=clean-ccache)

---

## Table of Contents

- [Overview](#overview)
- [Repository at a glance](#repository-at-a-glance)
- [Flashing disclaimer](#flashing-disclaimer)
- [Platform compatibility](#platform-compatibility)
- [Verified evidence](#verified-evidence)
- [On-device screenshots](#on-device-screenshots)
- [Features](#features)
- [Feature details](#feature-details)
- [How to use](#how-to-use)
- [Artifacts & releases](#artifacts--releases)
- [Adaptations](#adaptations)
- [Reproducibility](#reproducibility)
- [Local build](#local-build)
- [Repository layout](#repository-layout)
- [Customizations](docs/CUSTOMIZATIONS.md)
- [Roadmap & help wanted](#roadmap--help-wanted)
- [Credits](#credits)
- [License](#license)

---

## Overview

Builds a custom kernel for the **SM8750 (Snapdragon 8 Elite) platform** — the **OnePlus Ace 6** (codename `ktm`), running **Project Infinity X** (LineageOS-based, Android 16, kernel 6.6.142).

> **Naming note**: the overseas "OnePlus 15R" is the **Ace 6T** — a *different* device. This kernel targets the Ace 6 (`ktm`) only; do not flash it on a 15R / Ace 6T.

> **Test coverage**: only Project Infinity X has been tested. No compatibility claim is made for ColorOS/OxygenOS or for ROMs without device verification. See the [disclaimer](#flashing-disclaimer).

> **Repository scope**: CI fetches the kernel source from upstream `lineage-23.2` for each build. This repository stores the reviewed delta: patches, additional kernel sources, profiles, workflows and build rules. AK3 ZIPs remain local or CI candidates until the publication gate is satisfied.

Features are exposed as independent GitHub Actions inputs. Profile validation rejects only combinations with an explicit source or runtime conflict.

The kernel is built from the **official Ace6 kernel source** (lineage-23.2 branch) with **official prebuilt vendor modules** (from the ROM's vendor_dlkm). The current build path has these properties:

- The module tree is not rebuilt; UFS, GPU and related modules come from the ROM
- The device accepts the **commit-based kernel version string** produced by the current build path. An earlier vermagic workaround is not part of the current build (see [Verified evidence](#verified-evidence)).

## Repository at a glance

| | What |
|---|---|
| **9 feature patches** | Independent adaptations against the lineage-23.2 tree |
| **extra kernel sources** | SUSFS, EVDI, LZ4/LZ4KD/zstd, NTSYNC and Baseband Guard sources |
| **API adaptations** | SUSFS and Re:Kernel integrations are locked to the reviewed 6.6.142 source interfaces |
| **CI design** | shared profile/build entry, locked toolchain and artifact manifests; repository and WebUI gates are separate |
| **Verified on device** | ReSukiSU + SUSFS Inline boot/root/smoke/5-minute-soak evidence on one Ace 6; full feature acceptance is still incomplete |
| **Maintenance** | no fork tree to keep in sync — locked deltas are applied on demand against upstream `lineage-23.2` |

---

## Flashing disclaimer

> [!WARNING]
> This kernel was tested on **one device with one ROM**. Review the following information before flashing.

### Compatibility

| ROM | Status |
|---|---|
| **Project Infinity X** (v3.12, Android 16) | Tested and working (OnePlus Ace 6 `ktm`) |
| **LineageOS** (Ace6 builds) | Not tested; the kernel/modules/devicetrees follow the LineageOS tree, but device compatibility is unconfirmed |
| **ColorOS / OxygenOS** | **Not supported** — vendor integration differs from the target ROM |
| Anything else | Not assessed |

### Before flashing

1. **Back up the active boot partition** before flashing
2. **This kernel writes to the `boot` partition only** — do not write other partitions; an incorrect partition operation can prevent the device from booting
3. **The device must run a LineageOS-based ROM** (such as Infinity X); stock ColorOS/OxygenOS is outside the verified target
4. This is a **community project** with no warranty or guaranteed support

### Bootloop recovery

- Restore the backed-up stock boot image
- The stock `boot.img` is also extractable from the original ROM zip (`payload.bin`)

> [!CAUTION]
> **Only tested on Project Infinity X.** LineageOS and other ROMs are unverified. Back up the active boot partition and retain a recovery path before testing.

## Platform compatibility

### SM8750 platform

This project targets the **SM8750 (Snapdragon 8 Elite) platform** — the kernel, modules, and devicetree sources are all stock lineage-23.2 trees for the platform. The short ROM compatibility table lives in the [disclaimer](#flashing-disclaimer); the detailed scope is:

- The `lineage-23.2` SM8750 tree family is **shared across devices** — the same kernel/module/dtb trees underpin Ace6, other OnePlus SM8750 devices, and their LOS-based ROMs. What differs per device is the **vendor integration** (device-specific modules and firmware), so a kernel that boots one device may still refuse another.
- **Other OnePlus SM8750 devices** (if they use this tree family): unverified; no compatibility claim is made.

## Verified evidence

Measured on **OnePlus Ace 6 (`ktm`), Project Infinity X / Android 16** during the T26 run on 2026-09-06 and the main-profile follow-up on 2026-09-07:

| What | Evidence |
|---|---|
| **Kernel version** | `6.6.142-4k-g<12-digit-commit>` — real upstream commit in LOCALVERSION |
| **Boot/root/runtime smoke** | ReSukiSU + SUSFS Inline boots on Ace 6 `PLQ110`; root ADB, Wi-Fi/LTE/display/touch/sensor smoke and a five-minute read-only soak passed |
| **ReSukiSU** | v4.1.0 (build **35046**) — connects to KernelSU Manager |
| **Main-profile zram** | `lz4kd` default; nine compressor backends registered; `/dev/block/sda13` is attached as the 1 GiB writeback backing for the 6 GiB zram; one manual writeback trigger returned `rc=0` |
| **Module ownership** | `azram-backing` owns only the backing hand-off; Scene owns zram size/algorithm/swapon; ZramWritebackBoost owns writeback scheduling |
| **Vendor read-only** | `/vendor`, `/vendor_dlkm`, `/odm`, `/system_dlkm` all EROFS; write attempts rejected |

Remaining verification gaps:

- **Re:Kernel** is source/build-capable but remains experimental because the NoActive userspace protocol and runtime gate are unverified; no release claim is made
- **Droidspaces extend/EVDI** has kernel-side evidence, but container lifecycle, display userspace and frame submission were not tested
- **KPM/KPN** remains disabled and has not been exercised on a real device
- **LineageOS** (official Ace6 builds) remains unverified; the test device runs Project Infinity X

## On-device screenshots

Taken on the same test device (OnePlus Ace 6 `ktm`, Project Infinity X v3.12). Click any thumbnail for the full-resolution image.

<table>
  <tr>
    <td align="center"><a href="docs/screenshots/ksu_manager.png"><img src="docs/screenshots/ksu_manager.png" width="150" alt="ReSukiSU"></a></td>
    <td align="center"><a href="docs/screenshots/susfs.png"><img src="docs/screenshots/susfs.png" width="150" alt="SuSFS"></a></td>
    <td align="center"><a href="docs/screenshots/zram_all_algos.png"><img src="docs/screenshots/zram_all_algos.png" width="150" alt="Zram algorithms"></a></td>
    <td align="center"><a href="docs/screenshots/zram_writeback.png"><img src="docs/screenshots/zram_writeback.png" width="150" alt="LZ4KD + writeback"></a></td>
    <td align="center"><a href="docs/screenshots/droidspaces.png"><img src="docs/screenshots/droidspaces.png" width="150" alt="Droidspaces"></a></td>
  </tr>
  <tr>
    <td align="center"><b>① ReSukiSU</b></td>
    <td align="center"><b>② SuSFS</b></td>
    <td align="center"><b>③ Zram algorithms</b></td>
    <td align="center"><b>④ LZ4KD + writeback</b></td>
    <td align="center"><b>⑤ Droidspaces</b></td>
  </tr>
  <tr>
    <td align="center"><a href="docs/screenshots/bbg_erofs.png"><img src="docs/screenshots/bbg_erofs.png" width="150" alt="Baseband Guard"></a></td>
    <td align="center"><a href="docs/screenshots/network.png"><img src="docs/screenshots/network.png" width="150" alt="Better network"></a></td>
    <td align="center"><a href="docs/screenshots/banner.png"><img src="docs/screenshots/banner.png" width="150" alt="Build tags"></a></td>
    <td align="center"><a href="docs/screenshots/rekernel.png"><img src="docs/screenshots/rekernel.png" width="150" alt="Re:Kernel"></a></td>
    <td align="center"><a href="docs/screenshots/bbr.png"><img src="docs/screenshots/bbr.png" width="150" alt="BBR"></a></td>
  </tr>
  <tr>
    <td align="center"><b>⑥ Baseband Guard</b></td>
    <td align="center"><b>⑦ Better network</b></td>
    <td align="center"><b>⑧ Build tags</b></td>
    <td align="center"><b>⑨ Re:Kernel</b></td>
    <td align="center"><b>⑩ BBR</b></td>
  </tr>
</table>

Still pending: **KPM/KPN** (not tested on device yet).

---

## Features

| Feature | Default | Description |
|---|---|---|
| **KernelSU** | `none` | ReSukiSU (built-in KSU) or none |
| **SUSFS** | off | Enhanced mount/root hiding (needs KSU) |
| **lz4 1.10 + zstd 1.5.7** | off | Compression performance (newer algorithms, ARM64 NEON) |
| **LZ4KD** | off | Additional lz4 variant for zram |
| **All zram algorithms** | off | Enable every zram compressor in `comp_algorithm`, including lz4hc and 842 for container/Droidspaces use |
| **ZRAM writeback** | off | Write idle/incompressible zram pages to a backing device (needs runtime `backing_dev` config) |
| **Droidspaces** | off | Lightweight Linux container support (standard/extend) |
| **Baseband Guard** | off | Kernel-level anti-format protection |
| **CVE patches** | off | GhostLock (CVE-2026-43499 + CVE-2026-53163) — upstream now ships both, patch removed |
| **Better network** | off | ipset/iptables advanced network support |
| **BBR** | off | TCP congestion control |
| **KPM/KPN** | off | KernelPatch Next (independent kernel patch support) |
| **Re:Kernel** | off | Freezer/NoActive binder notification hooks |
| **Kernel suffix** | empty | Custom version suffix (e.g. `perf` → `6.6.142-4k-perf`) |
| **Attribution** | on | Build tags (user/host/REPO_NAME/AK3) |
| **Artifacts** | ak3 | `ak3` candidate zip; raw `Image` is local-only and `boot.img`/`all` are blocked |
| 🕐 **Build time** | empty | Custom build timestamp (`KBUILD_BUILD_TIMESTAMP`). On CI all build timestamps are fixed to `2025-05-25` via faketime for reproducibility — a custom value overrides the kernel-embedded one. Locally (reproduce.sh) empty = current UTC |
| 💾 **Public ccache** | off | Upload build cache to Release for fast rebuilds |
| 🔍 **ccache debug** | off | Upload ccache logs |

---

## Feature details

### KernelSU (ReSukiSU)

- Clones [ReSukiSU](https://github.com/ReSukiSU/ReSukiSU) (full history — version number = `30000 + commit count + 700`)
- Applies the 7 mandatory manual hooks (execveat/stat/faccessat/sys_read/sys_reboot/input/setresuid)
- Verified with version 35046 (`v4.1.0`)

### SUSFS

- From [simonpunk/susfs4ksu](https://gitlab.com/simonpunk/susfs4ksu) (`gki-android15-6.6` branch)
- 25 main-tree files + 16 KernelSU-internal adaptation files
- Includes all susfs features: sus_path, sus_mount, sus_kstat, uname spoofing, cmdline spoofing, open_redirect, sus_map, AVC log spoofing

### Droidspaces

- `standard`: containers + ntsync (NT synchronization primitives)
- `extend`: + EVDI virtual display, virtual HCI, systemd-coredump
- Kernel configs: PID_NS/USER_NS/SYSVIPC/DEVTMPFS/POSIX_MQUEUE/namespaces

### Re:Kernel

- **Source integration**: netlink server + binder hooks (reply/transaction/free_buffer_full) + signal hooks; the LKM route was not retained because the target tree does not expose the required hooks
- All wrapped in `#ifdef CONFIG_REKERNEL` — no Re:Kernel code is compiled when disabled
- Adapted for the `lineage-23.2` tree (6.6.142): `proc_ops` API, different `binder_alloc`/`signal.c` signatures

> **Known limitation — NoActive allowlist**: Photo Picker (**Photos and videos** permission → **Allow limited access** mode) remains on an empty loading screen and the wallpaper cannot be changed when **Google Photos is not allowlisted** in NoActive. During deep sleep/freeze, suspended apps stop consuming binder transactions: media.module's call into Photos does not return, its binder pool stalls, and the picker queues indefinitely. `system_server` binder threads can also remain blocked on pending synchronous transactions to other frozen Google apps (GMS/Maps/Gmail/Chrome). Diagnose with `adb shell su -c "cat /dev/binderfs/binder_logs/transactions"`; inspect transactions with large `elapsed` values and resolve PIDs with `ps -A -o pid=,args=`. Add **Google Photos** and any required Google apps to the NoActive allowlist before testing.

### Baseband Guard

- From [cctv18/Baseband-guard](https://github.com/cctv18/Baseband-guard)
- LSM-based anti-format protection (blocks writes to non-user partitions)

### GhostLock (CVE-2026-43499 + CVE-2026-53163)

Both vulnerabilities are now covered by upstream `lineage-23.2` itself:
- **CVE-2026-43499**: rtmutex `remove_waiter` NULL guard — present in the locked upstream 6.6.142 tree (`scoped_guard`)
- **CVE-2026-53163**: proxy cleanup `ret < 0` fix in `rtmutex_api.c` — merged upstream as `UPSTREAM: locking/rtmutex: Skip remove_waiter() when waiter is not enqueued` (pushed to `lineage-23.2` on 2026-08-18)

The standalone `08_cve.patch` was therefore removed.

### Compression

- lz4 1.10 (new library structure, ARM64 NEON fast decompress)
- zstd 1.5.7
- LZ4KD (from [ShirkNeko/SukiSU_patch](https://github.com/ShirkNeko/SukiSU_patch)) — independent algorithm for zram

---

## How to use

### First fork (one-time setup)

1. **Fork** this repository
2. **Allow write permissions**: Settings → Actions → General → Workflow permissions → **Read and write** (required for Release uploads)
3. Run the **Upload AOSP Clang Toolchain** workflow once. It packages the official toolchain (clang 21.0.0 r563880c, about 1.5 GB) in the fork's Release; the build downloads it there because no apt fallback is configured.
4. Push a commit to the default branch to activate the weekly report-only upstream drift check

### Build

1. Go to **Actions** → **Build Ace6 Kernel** → **Run workflow**
2. Select the required features, then click **Run workflow**
3. Download the AK3 zip from the run **artifacts** (or Release if `release_enable` is on)
4. The first build is cold; subsequent builds can reuse ccache. Build time depends on runner capacity and cache state.

### Debug checks

The **Debug build** workflow is manual and has three scopes:

- `fast` runs the repository gate, every feature-input combination, all profile dry-runs, the upstream checker entrypoint, and the WebUI build. It downloads no kernel source.
- `compile` builds three representative profiles with a compiler timeout and isolated evidence artifacts.
- `full` builds all seven profiles currently allowed through build preflight and adds the report-only upstream drift check.

The two standalone Droidspaces `extend` profiles remain expected blockers. The
fast job checks that they stop before source download; they are excluded from
the compile sets. Build jobs run at most two profiles at once and never update
the public ccache or publish a Release.

For the same local combination check:

```bash
python3 scripts/debug_combinations.py --json-out work/_tmp/debug-combinations.json
```

### Flash

1. **Back up the current slot's boot partition first** — via OrangeFox (OFRP) or any recovery's built-in backup, or:
   `adb shell "dd if=/dev/block/by-name/boot_$(getprop ro.boot.slot) of=/sdcard/boot_backup.img"`
2. Flash the AK3 zip (`Kernel-Ace6-*.zip`) via recovery (TWRP / OrangeFox / AOSP recovery): Install → select the zip → reboot. Or install it via the KernelSU manager (Install → flash image). AnyKernel3 targets the **active slot's `boot`** automatically (`boot_a` / `boot_b`, depending on the running slot)
3. **Partition requirement**: this kernel writes to `boot` only; it does not write to `init_boot` or the inactive slot
4. For a bootloop, restore the backed-up stock boot image

### Toolchain

- Uses **AOSP Clang 21.0.0 (r563880c)** — the exact same toolchain as the official OnePlus kernel build
- The build downloads it from the **`toolchain-AOSP-Clang-21.0.0-r563880c` Release of the fork**. The Upload step in "First fork" is required because the pipeline has no apt.llvm.org fallback.

### Notes

- Default workflow is a **minimal build** (no KSU, no features); select additional features explicitly
- `kernel_suffix` and `build_time` allow reproducible, identifiable builds
- Attribution defaults to `Lingguang@kernel-builder` — change via `build_user`/`build_host`, or disable entirely with `attribution_enable`

---

## Artifacts & releases

The repo keeps the kernel package, raw development output, and standalone KSU
modules in separate distribution paths:

| Output | Where | Flashable? | Notes |
|---|---|---|---|
| **AK3 zip** (`Kernel-Ace6-<user>-ksu<ver>-<date>.zip`) | selected `artifact_mode = ak3` | candidate for flashing | AnyKernel3 package; independent KSU modules are not embedded |
| **`Image`** | local `artifact_mode = image` only | Not flashable | raw development output; it has no target ramdisk/DTB/AVB packaging |
| **`boot.img` / `all`** | no output currently | Blocked | requires target boot inputs; the builder refuses to fabricate one |
| **standalone KSU module zips** | `independent_modules = true` | install separately in KernelSU | one zip per self-authored module; never silently inserted into AK3 |
| **`toolchain-…` / `ccache-…` Releases** | Releases tab | Not flashable | build infrastructure (toolchain / ccache), not kernels |

- Run artifacts are kept **14 days** (`retention-days` in `build.yml`); Releases are permanent
- Release tags look like `kernel-20260803-115320-ksu35046` — a point-in-time snapshot of the parameters used for that build
- Release publication remains a separate gate; `release_enable` is recorded as
  intent, while the workflow requires `release_allowed=true` after runtime,
  rollback and handoff evidence. Local builds never publish.

---

## Adaptations

This project adapts patches from several sources (primarily the [cctv18/oppo_oplus_realme_sm8750](https://github.com/cctv18/oppo_oplus_realme_sm8750) project, which targets the OnePlus official OKI tree) to the **Ace6 kernel tree** (`lineage-23.2`, kernel 6.6.142). Key adaptations:

- **Patches** are split into independent toggles (`patches/split/00-07, 09`): `07_compile_fixes.patch` applies unconditionally, the rest are gated by workflow features (KSU/SUSFS/lz4/LZ4KD/Droidspaces/BBG/Re:Kernel)
- **New files** (not created by the patch format) live in `patches/extra/` — lz4/zstd libs, susfs.c, evdi, ntsync, Baseband-guard
- **Re:Kernel** uses source hooks (netlink + binder/signal) adapted to the lineage-6.6.142 API
- **Modules** come from the ROM's official prebuilt `vendor_dlkm` — no need to rebuild the module tree
- Some OnePlus-official-only features (Fengchi scx governor, ADIOS IO scheduler) are **not ported** — their source exists only in the official OKI tree

## Reproducibility

- **Real commit** in LOCALVERSION (from GitHub API, since source is a zip without .git)
- **`KBUILD_BUILD_TIMESTAMP`** for custom/fixed build time
- **ccache** with sloppiness config (file mtime/ctime ignored) for fast rebuilds
- **Public ccache** (optional `ccache_update`): packages and uploads the cache to a Release for near-instant rebuilds
- **Upstream drift check**: `check_upstream.sh` (also a weekly workflow) cumulatively applies the locked steps to the latest `lineage-23.2` snapshot and uploads a JSON/Markdown report plus an Issue draft; it never creates or edits Issues automatically
- Verified locally: the shared entry produced five manifest-backed AK3 candidates; one ReSukiSU + SUSFS Inline candidate passed partial device acceptance. CI equivalence and full feature acceptance remain unclaimed.

**GitHub free-tier limits**: Actions provides 2,000 minutes per month and 1 GB of caches; this repository's ccache Release asset is about 630 MB and the toolchain asset about 1.5 GB. Repeated builds consume that allocation. Use `reproduce.sh` for frequent local builds and CI when a hosted runner is required.

---

## Local build

The repo includes a **cross-machine local build script** — `reproduce.sh`:

```bash
./reproduce.sh                          # minimal build (no features)
./reproduce.sh --ksu resukisu --susfs   # with ReSukiSU + SUSFS
./reproduce.sh --bbg --lz4 --lz4kd      # locked optional features
./reproduce.sh --dry-run                # validate IDs/locks without downloads
python3 scripts/ci.py                   # repository-only CI gate
```

`reproduce.sh` is a thin adapter around `scripts/build.py`, which is also called
by Actions. The common entry resolves the exact profile/source lock, clones
`KERNEL_SRC` into an isolated workspace instead of modifying it, applies the
ordered patches, runs `olddefconfig`, verifies the actual Image release string,
and writes a build manifest beside the AK3 output. Re:Kernel and the main
extend composition are build-capable with explicit runtime warnings; KPM remains
hard-blocked until its pinned resource is complete. See
`./reproduce.sh --help` and `docs/execution-t15.md`.

**Requirements**: the locked AOSP Clang 21 archive/toolchain, git, patch, zip,
make, bc, flex, bison, Python 3 and `strings`. Actions installs the host
packages and verifies the toolchain archive hash before the common entry runs.

**Directory hygiene**: all intermediates (sources, patched tree, AK3 pack dir)
live in `work/`; disposable logs/reports go to `work/_tmp/`; artifacts and
`build-manifest.json` go to `out/`.
`./reproduce.sh --clean` wipes only the selected work directory for a fresh
rebuild. Nothing is patched in an external source provider.

---

## Repository layout

```
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md         # Bug template: ROM, toggles, logs
│   │   └── bug_report_zh.md      # 中文 Bug 模板
│   └── workflows/
│       ├── ci.yml                 # Push/PR: repository and WebUI checks
│       ├── build.yml             # Main build workflow (manual trigger, 24 inputs)
│       ├── debug-build.yml        # Manual fast/profile/compile/drift checks
│       ├── clean-ccache.yml      # Manual: purge GitHub caches / Release ccache assets
│       ├── upstream-check.yml    # Weekly: do the patches still apply upstream?
│       └── upload-toolchain.yml  # One-time: upload AOSP clang to Release
├── patches/
│   ├── split/                    # 9 independent feature patches (00-07, 09)
│   ├── extra/                    # New files patches can't create
│   │   ├── fs/  crypto/  drivers/  include/  lib/
│   │   │                         # susfs.c, evdi, ntsync, lz4/lz4kd/zstd, headers
│   │   └── Baseband-guard/       # Anti-format LSM
│   └── 02_ksu.patch              # SUSFS KernelSU-internal adaptation
├── config/
│   └── config_ace6_final.config  # Base kernel config (from the device)
├── docs/
│   ├── CUSTOMIZATIONS.md         # Device-side modifications
│   ├── CUSTOMIZATIONS_zh.md      # 中文版
│   └── screenshots/              # 10 on-device proofs
├── modules/
│   ├── azram-backing/            # KSU module: hybridswap backing at boot (runs first)
│   ├── selinux_perf/             # KSU module: narrow perf-HAL SELinux allow
│   └── tcp-config/               # KSU module: TCP algo/qdisc WebUI
│       └── webui-src/            # WebUI build sources (npm + esbuild)
├── ak3/                          # AnyKernel3 template (tools/, META-INF/)
├── lib/                          # faketime libs + ccache-ECS
├── LICENSE
├── check_upstream.sh             # Report-only cumulative drift check wrapper
├── scripts/ci.py                 # Network-free repository CI gate
├── scripts/drift.py              # Snapshot checker and report/Issue-draft generator
└── reproduce.sh                  # Local build script
```

---

## Roadmap & help wanted

The build path is implemented and one profile has partial device evidence; release and feature gates remain open. Every item below is a concrete way to help:

**Looking for testers** — especially anyone on official LineageOS (Ace6): one confirmation report would close the biggest open question below.

| Item | Status | How to help |
|---|---|---|
| **Re:Kernel runtime verification** | ⛔ blocked by NoActive userspace/runtime gate | provide a named compatible userspace and device evidence |
| **KPM/KPN on-device test** | ⏳ toolchain ready, not exercised | load a KPM module, report what works/breaks |
| **LineageOS (Ace6) confirmation** | unverified | test on official LineageOS and submit an issue with the [bug template](.github/ISSUE_TEMPLATE/bug_report.md) |
| **Other SM8750 devices** | same tree family, unverified | provide device evidence after backing up `boot` |

**Maintenance**: upstream `lineage-23.2` and ReSukiSU changes are tracked. If a tree change prevents patch application, `reproduce.sh` reports the failure during the patch stage; submit an issue with the affected source and profile.

**Contributing**: see [CONTRIBUTING.md](CONTRIBUTING.md) for what makes a report or PR useful.

**Versions**: Release tags follow `kernel-<timestamp>-<feature-flags>` and identify the inputs used by one build. No upgrade path is defined; a tag or local AK3 zip is a candidate record and does not authorize publication.

**Planned features** (all need porting from the official OKI tree — the source is not in lineage):

- **Fengchi scx scheduler** — OnePlus's sched_ext governor
- **ADIOS IO scheduler** — OnePlus's custom block-layer scheduler
- **Official Ace6 120W SUPERVOOC charging** — kernel-side vooc protocol stack; the LOS ROM's vendor side may not cooperate, real-device charging is the verification target

These items are not scheduled. Status will be updated when implementation begins.

---

## Credits

This project incorporates work from the projects and developers listed below.

### Primary inspiration & patch sources

| Project | Used for |
|---|---|
| [cctv18/oppo_oplus_realme_sm8750](https://github.com/cctv18/oppo_oplus_realme_sm8750) | **Primary reference** — workflow design, patch structure, lz4/zstd/Droidspaces/BBG integration, ccache-ECS, faketime |
| [Ace6-Development/android_kernel_oneplus_sm8750](https://github.com/Ace6-Development/android_kernel_oneplus_sm8750) | Kernel source (lineage-23.2) |
| [Ace6-Development/android_kernel_oneplus_sm8750-modules](https://github.com/Ace6-Development/android_kernel_oneplus_sm8750-modules) | Module source (symbol link targets) |
| [LineageOS/android_kernel_oneplus_sm8750-devicetrees](https://github.com/LineageOS/android_kernel_oneplus_sm8750-devicetrees) | Device tree source |

### Feature sources

| Project | Used for |
|---|---|
| [ReSukiSU/ReSukiSU](https://github.com/ReSukiSU/ReSukiSU) | KernelSU implementation |
| [simonpunk/susfs4ksu](https://gitlab.com/simonpunk/susfs4ksu) | SUSFS kernel patches |
| [ShirkNeko/susfs4ksu](https://github.com/ShirkNeko/susfs4ksu) | SUSFS mirror |
| [Sakion-Team/Re-Kernel](https://github.com/Sakion-Team/Re-Kernel) | Re:Kernel source hooks |
| [KernelSU-Next/KPatch-Next](https://github.com/KernelSU-Next/KPatch-Next) | KPM/KPN toolchain |
| [ShirkNeko/SukiSU_patch](https://github.com/ShirkNeko/SukiSU_patch) | LZ4KD algorithm |
| [cctv18/Baseband-guard](https://github.com/cctv18/Baseband-guard) | Anti-format LSM |
| [ravindu644/Droidspaces-OSS](https://github.com/ravindu644/Droidspaces-OSS) | Droidspaces container |
| [zzh20188/GKI_KernelSU_SUSFS](https://github.com/zzh20188/GKI_KernelSU_SUSFS) | GhostLock CVE chain, build time, reference |

### Tools & infrastructure

| Project | Used for |
|---|---|
| [Android AOSP clang prebuilts](https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86) | Official toolchain (r563880c) |
| [osm0sis/AnyKernel3](https://github.com/osm0sis/AnyKernel3) | AK3 flashable zip template |
| [cctv18/ccache-ECS](https://github.com/cctv18/ccache-ECS) | Specialized kernel build cache |
| [ferstar/lz4-zstd](https://github.com/ferstar) | lz4/zstd algorithm updates (via cctv18) |
| [Xiaomichael](https://github.com/Xiaomichael) | lz4/zstd porting (via cctv18) |

### Special thanks

- [**@cctv18**](https://github.com/cctv18) — the entire build pipeline concept, patch integration, and ccache optimization approach
- [**@NullCode1337**](https://github.com/NullCode1337) — the Project Infinity X ROM and Ace6 kernel development
- **All upstream kernel/Android projects** that make custom kernels possible

---

## License

[GPL-2.0](LICENSE)
