# OnePlus Ace 6 Kernel Builder

> OnePlus Ace 6 / 15R (ktm, SM8750) custom kernel builder — configurable GitHub Actions build with ReSukiSU + SUSFS + Droidspaces + Re:Kernel support, verified on Project Infinity X (Android 16).

![GitHub Release](https://img.shields.io/github/v/release/GuLingguang/oneplus-sm8750-kernel-pro-build)
![GitHub License](https://img.shields.io/github/license/GuLingguang/oneplus-sm8750-kernel-pro-build)
![Workflow Status](https://img.shields.io/github/actions/workflow/status/GuLingguang/oneplus-sm8750-kernel-pro-build/build.yml?label=build&logo=githubactions)

---

## 📖 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Feature details](#feature-details)
- [How to use](#how-to-use)
- [Flashing disclaimer](#flashing-disclaimer-read-this-or-regret-it)
- [Adaptations & compromises](#adaptations--compromises)
- [Reproducibility](#reproducibility)
- [Local build](#local-build)
- [Repository layout](#repository-layout)
- [Credits](#credits)
- [License](#license)

---

## Overview

Builds a custom kernel for **OnePlus Ace 6 / 15R** (codename `ktm`, SM8750 / Snapdragon 8 Elite), running **Project Infinity X** (LineageOS-based, Android 16, kernel 6.6.139).

> ⚠️ **Only tested on Project Infinity X** — NOT for ColorOS/OxygenOS. Probably works on LineageOS (Ace6). See the [disclaimer](#flashing-disclaimer-read-this-or-regret-it).

Every feature is an **optional toggle** in GitHub Actions — build exactly what you need, nothing more.

The kernel is built from the **official Ace6 kernel source** (lineage-23.2 branch), with **official prebuilt vendor modules** (from the ROM's vendor_dlkm), which means:

- No need to rebuild the entire module tree (UFS/GPU/etc. come from the ROM)
- The kernel **vermagic does NOT need to be faked** — the device accepts kernels with a real commit-based version string (verified empirically: MODVERSIONS symbol checking is what matters, not the version string)
- The build follows the **real upstream commit** of the source tree

---

## ⚠️ Flashing disclaimer

> [!WARNING]
> This kernel was tested on **one device with one ROM** — please read before flashing.

### Compatibility

| ROM | Status |
|---|---|
| **Project Infinity X** (v3.12, Android 16) | ✅ Tested & working (OnePlus Ace 6 / 15R `ktm`) |
| **LineageOS** (Ace6 builds) | 🤔 Probably works — the kernel/modules/devicetrees are stock LineageOS with only non-destructive Ace6 additions (MPC7022 gauge, TMS NFC), but **not yet confirmed on a real device** |
| **ColorOS / OxygenOS** | ❌ **Not supported** — likely won't boot (different vendor integration) |
| Anything else | 🏴☠️ Unknown territory |

### Before you flash

1. **Back up your boot partition** — you will thank yourself later
2. **This kernel touches the `boot` partition only** — do not flash anything else (the device is already fused; messing with other partitions can brick it)
3. **Your device must run a LineageOS-based ROM** (like Infinity X) — this won't work on stock ColorOS/OxygenOS
4. This is a **community project** — there's no warranty, no support hotline, and no refunds

### If it bootloops

- Stay calm (or don't, we don't judge)
- Restore your stock boot image (that's why you backed up!)
- The stock `boot.img` is also extractable from the original ROM zip (`payload.bin`)

> [!CAUTION]
> **Only tested on Project Infinity X.** LineageOS is *probably* fine, ColorOS/OxygenOS is *probably* not. If in doubt, back up first and flash at your own risk.

## Features

| Feature | Default | Description |
|---|---|---|
| 🔗 **KernelSU** | `none` | ReSukiSU (built-in KSU) or none |
| 🛡️ **SUSFS** | off | Enhanced mount/root hiding (needs KSU) |
| ⚡ **lz4 1.10 + zstd 1.5.7** | off | Compression performance (newer algorithms, ARM64 NEON) |
| ⚡ **LZ4KD** | off | Additional lz4 variant for zram |
| 📦 **Droidspaces** | off | Lightweight Linux container support (standard/extend) |
| 🛡️ **Baseband Guard** | off | Kernel-level anti-format protection |
| 🔒 **CVE patches** | off | GhostLock (CVE-2026-43499 + CVE-2026-53163) |
| 🌐 **Better network** | off | ipset/iptables advanced network support |
| 🚀 **BBR** | off | TCP congestion control |
| 🧩 **KPM/KPN** | off | KernelPatch Next (independent kernel patch support) |
| 🔗 **Re:Kernel** | off | Freezer/NoActive binder notification hooks |
| 🏷️ **Kernel suffix** | empty | Custom version suffix (e.g. `perf` → `6.6.139-4k-perf`) |
| ✍️ **Attribution** | on | Build tags (user/host/REPO_NAME/AK3) |
| 📦 **Artifacts** | ak3 | `ak3` (flashable zip) or `all` (ak3 + Image + boot.img) |
| 🕐 **Build time** | empty | Custom build timestamp (`KBUILD_BUILD_TIMESTAMP`), empty = current UTC |
| 💾 **Public ccache** | off | Upload build cache to Release for fast rebuilds |
| 🔍 **ccache debug** | off | Upload ccache logs |

---

## Feature details

### 🔗 KernelSU (ReSukiSU)

- Clones [ReSukiSU](https://github.com/ReSukiSU/ReSukiSU) (full history — version number = `30000 + commit count + 700`)
- Applies the 7 mandatory manual hooks (execveat/stat/faccessat/sys_read/sys_reboot/input/setresuid)
- Verified with version 35046 (`v4.1.0`)

### 🛡️ SUSFS

- From [simonpunk/susfs4ksu](https://gitlab.com/simonpunk/susfs4ksu) (`gki-android15-6.6` branch)
- 25 main-tree files + 16 KernelSU-internal adaptation files
- Includes all susfs features: sus_path, sus_mount, sus_kstat, uname spoofing, cmdline spoofing, open_redirect, sus_map, AVC log spoofing

### 📦 Droidspaces

- `standard`: containers + ntsync (NT synchronization primitives)
- `extend`: + EVDI virtual display, virtual HCI, systemd-coredump
- Kernel configs: PID_NS/USER_NS/SYSVIPC/DEVTMPFS/POSIX_MQUEUE/namespaces

### 🔗 Re:Kernel

- **Source integration** (not LKM): netlink server + binder hooks (reply/transaction/free_buffer_full) + signal hooks
- All wrapped in `#ifdef CONFIG_REKERNEL` — zero impact when disabled
- Adapted for the `lineage-23.2` tree (6.6.139): `proc_ops` API, different `binder_alloc`/`signal.c` signatures

### 🛡️ Baseband Guard

- From [cctv18/Baseband-guard](https://github.com/cctv18/Baseband-guard)
- LSM-based anti-format protection (blocks writes to non-user partitions)

### 🔒 GhostLock (CVE-2026-43499 + CVE-2026-53163)

Both vulnerabilities are covered:
- **CVE-2026-43499**: rtmutex `remove_waiter` NULL guard — already present in the upstream 6.6.139 tree (`scoped_guard`)
- **CVE-2026-53163**: proxy cleanup `ret < 0` fix in `rtmutex_api.c`

### ⚡ Compression

- lz4 1.10 (new library structure, ARM64 NEON fast decompress)
- zstd 1.5.7
- LZ4KD (from [ShirkNeko/SukiSU_patch](https://github.com/ShirkNeko/SukiSU_patch)) — independent algorithm for zram

---

## How to use

1. **Fork** this repository
2. Go to **Actions** → **Build Ace6 Kernel** → **Run workflow**
3. Toggle features as desired, click **Run workflow**
4. Download the AK3 zip from the run **artifacts** (or Release if `release_enable` is on)

### Toolchain

- Uses **AOSP Clang 21.0.0 (r563880c)** — the exact same toolchain as the official OnePlus kernel build (from the `AOSP-Clang-21.0.0-r563880c` Release of this repo)
- clang-21 installed via apt.llvm.org, or downloaded from the Release asset

### Notes

- Default workflow is a **minimal build** (no KSU, no features) — enable what you need
- `kernel_suffix` and `build_time` allow reproducible, identifiable builds
- Attribution defaults to `Lingguang@kernel-builder` — change via `build_user`/`build_host`, or disable entirely with `attribution_enable`

---

## Adaptations & compromises

This project adapts patches from several sources to the **Ace6 kernel tree** (branch `lineage-23.2`, kernel 6.6.139), which differs from the original targets of those patches. Key differences:

### vs. [cctv18/oppo_oplus_realme_sm8750](https://github.com/cctv18/oppo_oplus_realme_sm8750)

| Aspect | cctv18 | This project |
|---|---|---|
| Kernel base | OnePlus official OKI (6.6.89) | **Ace6 lineage-23.2 (6.6.139)** |
| Modules | Built from source | **Official prebuilt vendor_dlkm** (from ROM) |
| vermagic | Faked to match | **Real commit** (verified working without matching) |
| 风驰 scx governor | Yes (official tree) | **Not ported** (needs official OKI tree) |
| ADIOS IO scheduler | Yes (official tree) | **Not ported** (source in official tree only) |
| Re:Kernel | LKM approach | **Source integration** (adapted) |
| KSU variants | 5 (ReSukiSU/SukiSU-Ultra/KSU-Next/KSU/none) | **ReSukiSU/none** (the others untested on this device) |

### Patch structure

The original monolithic patch is **split into 10 independent patches** (`patches/split/00-09`), each tied to one feature toggle:

```
00_ksu_hooks.patch      KSU manual hooks (mandatory when KSU enabled)
01_susfs_main.patch     SUSFS main tree
02_lz4.patch            lz4 1.10
03_zstd.patch           zstd 1.5.7
04_lz4kd.patch          LZ4KD
05_droidspaces.patch    Droidspaces
06_baseband_guard.patch Baseband Guard
07_compile_fixes.patch  Compile fixes (always applied)
08_cve.patch            GhostLock CVE
09_rekernel.patch       Re:Kernel
```

Plus `patches/extra/` — **new files** that patches can't create (lz4/zstd new libs, susfs.c, evdi driver, ntsync, Baseband-guard source, LZ4KD source).

### Things we deliberately did NOT adopt

- **`-Wno-error`** (cctv18 uses it) — we prefer errors to be visible (they caught real bugs in adaptation)
- **`O=out`** separate output dir — no benefit for our one-shot builds (we use fresh source zips each time)
- **`kernel_suffix` as version replacement** — we keep the real commit, suffix is optional addition
- **KPM/KPN** — available as option, but noted as potentially conflicting with ReSukiSU's built-in kpm

---

## Reproducibility

- **Real commit** in LOCALVERSION (from GitHub API, since source is a zip without .git)
- **`KBUILD_BUILD_TIMESTAMP`** for custom/fixed build time
- **ccache** with sloppiness config (file mtime/ctime ignored) for fast rebuilds
- **Public ccache** (optional `ccache_update`): packages and uploads the cache to a Release for near-instant rebuilds
- Verified: GitHub Actions produces a bootable AK3 with the exact configured features

---

## Local build

The repo includes a **cross-machine local build script** — `reproduce.sh`:

```bash
./reproduce.sh                          # minimal build (no features)
./reproduce.sh --ksu resukisu --susfs   # with ReSukiSU + SUSFS
./reproduce.sh --rekernel --bbg --lz4   # more features
```

It auto-detects clang 21 (multiple paths), downloads sources (or uses `KERNEL_SRC`), applies patches by toggle, copies extra files, sets the real commit, and produces an AK3 zip. See `./reproduce.sh --help`.

**Requirements**: clang 21 (Arch: `pacman -S clang21 lld21 llvm21`; Ubuntu: apt.llvm.org), git, patch, unzip, zip, curl, make.

---

## Repository layout

```
├── .github/workflows/
│   ├── build.yml              # Main build workflow (manual trigger)
│   └── upload-toolchain.yml   # One-time: upload AOSP clang to Release
├── patches/
│   ├── split/                 # 10 independent feature patches
│   ├── extra/                 # New files patches can't create
│   └── 02_ksu.patch           # SUSFS KernelSU-internal adaptation
├── config/                    # Base kernel config (from device)
├── ak3/                       # AnyKernel3 template
├── lib/                       # faketime libs + ccache-ECS
└── reproduce.sh               # Local build script
```

---

## Credits

This project builds upon the work of many projects and developers. Thank you!

### 🏆 Primary inspiration & patch sources

| Project | Used for |
|---|---|
| [cctv18/oppo_oplus_realme_sm8750](https://github.com/cctv18/oppo_oplus_realme_sm8750) | **Primary reference** — workflow design, patch structure, lz4/zstd/Droidspaces/BBG integration, ccache-ECS, faketime |
| [Ace6-Development/android_kernel_oneplus_sm8750](https://github.com/Ace6-Development/android_kernel_oneplus_sm8750) | Kernel source (lineage-23.2) |
| [Ace6-Development/android_kernel_oneplus_sm8750-modules](https://github.com/Ace6-Development/android_kernel_oneplus_sm8750-modules) | Module source (symbol link targets) |
| [LineageOS/android_kernel_oneplus_sm8750-devicetrees](https://github.com/LineageOS/android_kernel_oneplus_sm8750-devicetrees) | Device tree source |

### 🧩 Feature sources

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

### 🛠️ Tools & infrastructure

| Project | Used for |
|---|---|
| [Android AOSP clang prebuilts](https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86) | Official toolchain (r563880c) |
| [osm0sis/AnyKernel3](https://github.com/osm0sis/AnyKernel3) | AK3 flashable zip template |
| [cctv18/ccache-ECS](https://github.com/cctv18/ccache-ECS) | Specialized kernel build cache |
| [ferstar/lz4-zstd](https://github.com/ferstar) | lz4/zstd algorithm updates (via cctv18) |
| [Xiaomichael](https://github.com/Xiaomichael) | lz4/zstd porting (via cctv18) |

### 🙏 Special thanks

- **cctv18** (酷安) — the entire build pipeline concept, patch integration, and ccache optimization approach
- **NullCode1337** — the Project Infinity X ROM and Ace6 kernel development
- **All upstream kernel/Android projects** that make custom kernels possible

---

## License

[GPL-2.0](LICENSE)
