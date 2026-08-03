# OnePlus Ace 6 Kernel Builder

> OnePlus Ace 6 / 15R (ktm, SM8750) custom kernel builder — configurable GitHub Actions build with ReSukiSU + SUSFS + Droidspaces + Re:Kernel support.

![GitHub Release](https://img.shields.io/github/v/release/GuLingguang/oneplus-sm8750-kernel-pro-build)
![GitHub License](https://img.shields.io/github/license/GuLingguang/oneplus-sm8750-kernel-pro-build)

## Overview

Builds a custom kernel for OnePlus Ace 6 / 15R (codename `ktm`, SM8750 / Snapdragon 8 Elite), running **Project Infinity X** (LineageOS-based, Android 16).

Fully configurable via GitHub Actions — every feature is an optional toggle.

## Features

| Feature | Default | Description |
|---|---|---|
| 🔗 KernelSU | `none` | ReSukiSU (built-in KSU) or none |
| 🛡️ SUSFS | off | Enhanced mount/root hiding (needs KSU) |
| ⚡ lz4 1.10 + zstd 1.5.7 | off | Compression performance |
| ⚡ LZ4KD | off | Additional lz4 variant for zram |
| 📦 Droidspaces | off | Linux container support (standard/extend) |
| 🛡️ Baseband Guard | off | Anti-format protection |
| 🔒 CVE patches | off | GhostLock (CVE-2026-43499/53163) |
| 🌐 Better network | off | ipset/iptables advanced support |
| 🚀 BBR | off | TCP congestion control |
| 🧩 KPM/KPN | off | KernelPatch Next support |
| 🔗 Re:Kernel | off | Freezer/NoActive binder notification |
| 🏷️ Kernel suffix | empty | Custom version suffix |
| ✍️ Attribution | on | Build tags (user/host/REPO_NAME) |
| 📦 Artifacts | ak3 | ak3 or all (ak3+Image+boot.img) |

## How to use

1. **Fork** this repository
2. Go to **Actions** → **Build Ace6 Kernel** → **Run workflow**
3. Toggle features as desired, click **Run workflow**
4. Download the AK3 zip from the run artifacts (or Release if enabled)

### Build time customization

Set `build_time` (e.g. `Sun Dec 01 08:10:00 UTC 2024`) for a reproducible build timestamp, or leave empty for current UTC.

## Kernel sources

- [Ace6-Development/android_kernel_oneplus_sm8750](https://github.com/Ace6-Development/android_kernel_oneplus_sm8750) — main kernel (lineage-23.2)
- [Ace6-Development/android_kernel_oneplus_sm8750-modules](https://github.com/Ace6-Development/android_kernel_oneplus_sm8750-modules) — modules
- [LineageOS/android_kernel_oneplus_sm8750-devicetrees](https://github.com/LineageOS/android_kernel_oneplus_sm8750-devicetrees) — device trees

## Reproducibility

- Fixed commit-based LOCALVERSION (or custom suffix)
- `KBUILD_BUILD_TIMESTAMP` for custom build time
- ccache (with sloppiness) for fast rebuilds
- Public ccache cache via Release (optional, `ccache_update`)

## Local build

See `reproduce.sh` for a local one-click build (requires clang 21 + kernel sources).

## License

[GPL-2.0](LICENSE)
