#!/usr/bin/env bash
# ============================================================
# Ace6 (ktm) custom kernel local build script (cross-machine)
# Aligned with the GitHub Actions workflow: real commit + extra files + toggles
#
# Usage:
#   ./reproduce.sh                            # minimal (no features)
#   ./reproduce.sh --ksu resukisu --susfs     # with ReSukiSU + SUSFS
#
# Options:
#   --ksu <resukisu|none>   KernelSU (default: none)
#   --susfs                 SUSFS (requires --ksu resukisu)
#   --lz4                   lz4+zstd
#   --lz4kd                 LZ4KD
#   --droidspaces <std|ext> Droidspaces
#   --bbg                   Baseband Guard
#   --cve                   CVE patches
#   --bbr                   BBR
#   --kpm                   KPM
#   --rekernel              Re:Kernel
#   --suffix <name>         kernel suffix
#   --user <name>           attribution user (default: Lingguang)
#   --host <name>           attribution host (default: kernel-builder)
#   --no-attribution        disable attribution
#   --time "<str>"          custom build time
#   --out <dir>             output dir (default: out/)
#
# Env vars:
#   REPO_BASE=...           repo base (default https://github.com)
#   KERNEL_SRC=...          existing kernel source (skip download; patches applied in-place!)
# ============================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_DIR="${WORK_DIR:-$REPO_DIR/work}"
OUT_DIR="${OUT_DIR:-$REPO_DIR/out}"
REPO_BASE="${REPO_BASE:-https://github.com}"
BUILD_USER="Lingguang"
BUILD_HOST="kernel-builder"
ATTRIBUTION=1
BUILD_TIME=""
KSU="none"
SUSFS=0; LZ4=0; LZ4KD=0; DROIDSPACES="false"; BBG=0; CVE=0; BBR=0; KPM=0; REKERNEL=0
SUFFIX=""

# ---- Parse args ----
while [ $# -gt 0 ]; do
  case "$1" in
    --ksu) KSU="$2"; shift 2 ;;
    --susfs) SUSFS=1; shift ;;
    --lz4) LZ4=1; shift ;;
    --lz4kd) LZ4KD=1; shift ;;
    --droidspaces) DROIDSPACES="$2"; shift 2 ;;
    --bbg) BBG=1; shift ;;
    --cve) CVE=1; shift ;;
    --bbr) BBR=1; shift ;;
    --kpm) KPM=1; shift ;;
    --rekernel) REKERNEL=1; shift ;;
    --suffix) SUFFIX="$2"; shift 2 ;;
    --user) BUILD_USER="$2"; shift 2 ;;
    --host) BUILD_HOST="$2"; shift 2 ;;
    --no-attribution) ATTRIBUTION=0; shift ;;
    --time) BUILD_TIME="$2"; shift 2 ;;
    --out) OUT_DIR="$2"; shift 2 ;;
    -h|--help) grep "^#" "$0" | head -35; exit 0 ;;
    *) echo "未知参数: $1"; exit 1 ;;
  esac
done

log() { echo -e "\033[1;34m===\033[0m $*"; }
die() { echo -e "\033[1;31m错误:\033[0m $*" >&2; exit 1; }

# ---- [0] Dependency check ----
log "[0] 依赖检查"
need_cmd() { command -v "$1" >/dev/null 2>&1 || die "missing command: $1"; }
need_cmd git; need_cmd patch; need_cmd unzip; need_cmd zip; need_cmd curl; need_cmd make

# Detect clang 21 (multi-path, cross-machine)
CLANG_FOUND=""
for c in clang clang-21 /usr/lib/llvm21/bin/clang /usr/lib/llvm-21/bin/clang; do
  if command -v "$c" >/dev/null 2>&1 && "$c" --version 2>/dev/null | grep -q "clang version 2[01]"; then
    CLANG_FOUND="$c"; break
  fi
done
[ -z "$CLANG_FOUND" ] && die "clang 21 required (Arch: pacman -S clang21 lld21 llvm21; Ubuntu: apt.llvm.org)"
CLANG_BIN="$(dirname "$(command -v "$CLANG_FOUND")")"
export PATH="$CLANG_BIN:$PATH"
export LLVM=1 LLVM_IAS=1
echo "clang: $("$CLANG_FOUND" --version | head -1)"

# ---- [1] Prepare sources (3 repos) ----
log "[1] 准备源码"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"
if [ -z "${KERNEL_SRC:-}" ]; then
  [ -d src ] || {
    log "  Download kernel source (lineage-23.2)..."
    curl -sL "$REPO_BASE/GuLingguang/oneplus-sm8750-kernel-pro/archive/refs/heads/lineage-23.2.zip" -o src.zip
    unzip -q src.zip && mv oneplus-sm8750-kernel-pro-lineage-23.2 src && rm src.zip
  }
  [ -d sm8750-modules ] || {
    curl -sL "$REPO_BASE/Ace6-Development/android_kernel_oneplus_sm8750-modules/archive/refs/heads/lineage-23.2.zip" -o modules.zip
    unzip -q modules.zip && mv android_kernel_oneplus_sm8750-modules-lineage-23.2 sm8750-modules && rm modules.zip
  }
  [ -d sm8750-devicetrees ] || {
    curl -sL "$REPO_BASE/LineageOS/android_kernel_oneplus_sm8750-devicetrees/archive/refs/heads/lineage-23.2.zip" -o dt.zip
    unzip -q dt.zip && mv android_kernel_oneplus_sm8750-devicetrees-lineage-23.2 sm8750-devicetrees && rm dt.zip
  }
  SRC_DIR="$WORK_DIR/src"
else
  SRC_DIR="$KERNEL_SRC"
fi
cd "$SRC_DIR"
# Get real commit (zip has no .git)
SRC_COMMIT=$(curl -sL "$REPO_BASE/GuLingguang/oneplus-sm8750-kernel-pro/commits/lineage-23.2" | grep -oE '"sha": "[0-9a-f]{40}"' | head -1 | grep -oE '[0-9a-f]{40}' || true)
echo "  Source commit: ${SRC_COMMIT:-unknown}"

# ---- [2] Apply patches (by toggle) ----
log "[2] 应用补丁"
apply() { patch -p1 -F3 --batch -f < "$REPO_DIR/patches/split/$1" || die "patch $1 failed"; }
apply 07_compile_fixes.patch
[ "$KSU" != "none" ] && apply 00_ksu_hooks.patch
[ "$SUSFS" = "1" ] && [ "$KSU" != "none" ] && apply 01_susfs_main.patch
[ "$LZ4" = "1" ] && { apply 02_lz4.patch; apply 03_zstd.patch; }
[ "$LZ4KD" = "1" ] && apply 04_lz4kd.patch
[ "$DROIDSPACES" != "false" ] && apply 05_droidspaces.patch
[ "$BBG" = "1" ] && apply 06_baseband_guard.patch
[ "$CVE" = "1" ] && apply 08_cve.patch
[ "$REKERNEL" = "1" ] && apply 09_rekernel.patch

# ---- [3] Copy extra files ----
log "[3] 复制 extra 文件"
[ "$SUSFS" = "1" ] && [ "$KSU" != "none" ] && {
  cp -r "$REPO_DIR/patches/extra/fs/susfs.c" fs/
  cp -r "$REPO_DIR/patches/extra/include/linux/susfs.h" "$REPO_DIR/patches/extra/include/linux/susfs_def.h" include/linux/
}
[ "$LZ4" = "1" ] && {
  cp -r "$REPO_DIR/patches/extra/lib/lz4" lib/
  cp "$REPO_DIR/patches/extra/lib/zstd/common/allocations.h" "$REPO_DIR/patches/extra/lib/zstd/common/bits.h" lib/zstd/common/
  cp "$REPO_DIR/patches/extra/lib/zstd/compress/zstd_preSplit.c" "$REPO_DIR/patches/extra/lib/zstd/compress/zstd_preSplit.h" lib/zstd/compress/
}
[ "$LZ4KD" = "1" ] && {
  cp "$REPO_DIR/patches/extra/crypto/lz4k.c" "$REPO_DIR/patches/extra/crypto/lz4kd.c" crypto/
  cp "$REPO_DIR/patches/extra/include/linux/lz4k.h" "$REPO_DIR/patches/extra/include/linux/lz4kd.h" include/linux/
  cp -r "$REPO_DIR/patches/extra/lib/lz4k" "$REPO_DIR/patches/extra/lib/lz4kd" lib/
}
[ "$DROIDSPACES" != "false" ] && {
  cp "$REPO_DIR/patches/extra/drivers/misc/ntsync.c" drivers/misc/
  cp "$REPO_DIR/patches/extra/include/uapi/linux/ntsync.h" include/uapi/linux/
  cp -r "$REPO_DIR/patches/extra/drivers/gpu/drm/evdi" drivers/gpu/drm/
}
[ "$BBG" = "1" ] && {
  cp -r "$REPO_DIR/patches/extra/Baseband-guard" .
  ln -sfn ../Baseband-guard security/baseband-guard
}

# ---- [4] KernelSU ----
if [ "$KSU" != "none" ]; then
  log "[4] 集成 KernelSU ($KSU)"
  [ -d KernelSU ] || git clone "$REPO_BASE/ReSukiSU/ReSukiSU.git" KernelSU
  ln -sfn ../KernelSU/kernel drivers/kernelsu
  grep -q "kernelsu" drivers/Makefile || echo 'obj-$(CONFIG_KSU) += kernelsu/' >> drivers/Makefile
  grep -q "drivers/kernelsu/Kconfig" drivers/Kconfig || sed -i "/endmenu/i\source \"drivers/kernelsu/Kconfig\"" drivers/Kconfig
  [ "$SUSFS" = "1" ] && (cd KernelSU && git apply "$REPO_DIR/patches/02_ksu.patch" 2>/dev/null || echo "⚠ 02_ksu.patch needs manual adaptation")
  [ "$ATTRIBUTION" = "1" ] && sed -i "s/^REPO_NAME := .*/REPO_NAME := $BUILD_USER/" KernelSU/kernel/Kbuild
fi

# ---- [5] Deploy config ----
log "[5] 部署配置"
cp "$REPO_DIR/config/config_ace6_final.config" .config
[ "$KSU" = "none" ] && ./scripts/config --file .config -d CONFIG_KSU -d CONFIG_KSU_SUSFS
[ "$SUSFS" != "1" ] || [ "$KSU" = "none" ] && ./scripts/config --file .config -d CONFIG_KSU_SUSFS
if [ -n "$SUFFIX" ]; then
  ./scripts/config --file .config --set-str CONFIG_LOCALVERSION "-4k-$SUFFIX"
else
  [ -n "$SRC_COMMIT" ] && ./scripts/config --file .config --set-str CONFIG_LOCALVERSION "-4k-g${SRC_COMMIT:0:12}"
fi
./scripts/config --file .config -d CONFIG_LOCALVERSION_AUTO
[ "$LZ4KD" != "1" ] && ./scripts/config --file .config -d CONFIG_LZ4K_COMPRESS -d CONFIG_LZ4KD_COMPRESS -d CONFIG_CRYPTO_LZ4K -d CONFIG_CRYPTO_LZ4KD
[ "$DROIDSPACES" = "false" ] && ./scripts/config --file .config -d CONFIG_SYSVIPC -d CONFIG_NTSYNC -d CONFIG_DRM_LINDROID_EVDI
[ "$DROIDSPACES" != "extend" ] && ./scripts/config --file .config -d CONFIG_DRM_LINDROID_EVDI
[ "$BBG" != "1" ] && ./scripts/config --file .config -d CONFIG_BBG
[ "$REKERNEL" = "1" ] && ./scripts/config --file .config -e CONFIG_REKERNEL
[ "$BBR" = "1" ] && ./scripts/config --file .config -e CONFIG_TCP_CONG_ADVANCED -e CONFIG_TCP_CONG_BBR
make LLVM=1 LLVM_IAS=1 ARCH=arm64 olddefconfig >/dev/null 2>&1

# ---- [6] Build ----
log "[6] Build kernel (-j$(nproc))"
export KBUILD_BUILD_USER="$BUILD_USER"
export KBUILD_BUILD_HOST="$BUILD_HOST"
if [ -n "$BUILD_TIME" ] && [ "$BUILD_TIME" != "N" ] && [ "$BUILD_TIME" != "n" ]; then
  export KBUILD_BUILD_TIMESTAMP="$BUILD_TIME"
fi
[ "$ATTRIBUTION" = "0" ] && { export KBUILD_BUILD_USER=""; export KBUILD_BUILD_HOST=""; }
make LLVM=1 LLVM_IAS=1 ARCH=arm64 -j$(nproc) Image
[ -f arch/arm64/boot/Image ] || die "build did not produce Image"

# ---- [7] Verify ----
log "[7] 验证产物"
strings arch/arm64/boot/Image | grep -q "Linux version 6.6.139" || die "version string abnormal"

# ---- [8] Package AK3 ----
log "[8] Package AK3"
mkdir -p "$OUT_DIR" "$WORK_DIR/pack"
rm -rf "$WORK_DIR/pack"/*
cp -a "$REPO_DIR/ak3/." "$WORK_DIR/pack/"
cp arch/arm64/boot/Image "$WORK_DIR/pack/Image"
STAMP=$(date +%Y%m%d)
ZIP="Kernel-Ace6-$BUILD_USER-$STAMP.zip"
(cd "$WORK_DIR/pack" && zip -r9 "$OUT_DIR/$ZIP" . -x "*.git*" >/dev/null)
echo "Done: $OUT_DIR/$ZIP"
ls -lh "$OUT_DIR/$ZIP"
