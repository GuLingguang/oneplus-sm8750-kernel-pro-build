#!/usr/bin/env bash
# ============================================================
# Ace6 (ktm) 自定义内核一键构建脚本
# 复刻 2026-08-02 已刷成功最终版（ReSukiSU 35046 + SUSFS 2.2.0 + 全功能）
# 基线: android_kernel_oneplus_sm8750 @ d1ddd2498 (lineage-23.2)
# 工具链: clang 21 (21.1.8) + LLD 21
# 用法:
#   ./reproduce.sh                # 快照模式（默认，最忠实）
#   MODE=clone ./reproduce.sh     # 重新拉 ReSukiSU 主分支 + 适配补丁
#   环境变量:
#     SRC_DIR=...     工作树目录（默认 <repo>/work/src）
#     BUILD_USER=...  编译标签用户（默认 顾澪光）
#     BUILD_HOST=...  编译标签主机（默认 kernel-builder）
#     KSU_REPO=...    clone 模式用的 KSU 仓库（默认 ReSukiSU）
#     KSU_BRANCH=...  clone 模式分支（默认 main）
# ============================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="${SRC_DIR:-$REPO_DIR/work/src}"
MODULES_DIR="${MODULES_DIR:-$REPO_DIR/work/sm8750-modules}"
DT_DIR="${DT_DIR:-$REPO_DIR/work/sm8750-devicetrees}"
MODE="${MODE:-snapshot}"
BUILD_USER="${BUILD_USER:-顾澪光}"
BUILD_HOST="${BUILD_HOST:-kernel-builder}"
KSU_REPO="${KSU_REPO:-https://github.com/ReSukiSU/ReSukiSU.git}"
KSU_BRANCH="${KSU_BRANCH:-main}"
# 官方仓库（可被 REPO_BASE 覆盖，如代理 https://v6.gh-proxy.org/https://github.com）
REPO_BASE="${REPO_BASE:-https://github.com}"
BASE_COMMIT="d1ddd249869aa87f876b4edc76f18997e662316d"   # 基线提交（kernelsu 版本号相关）
MODULES_COMMIT="694285bd56d8f299816fae50e6aee18d492da37d" # sm8750-modules
DT_COMMIT="f287404c72b51928184d7abb034148b0e83a25b4"      # sm8750-devicetrees

PATCH_MAIN="$REPO_DIR/patches/01_mainline.patch"
PATCH_KSU="$REPO_DIR/patches/02_ksu.patch"
SNAP_TAR="$REPO_DIR/snapshot/repro_untracked.tar.gz"
CFG_FINAL="$REPO_DIR/config/config_ace6_final.config"
AK3_DIR="$REPO_DIR/ak3"

log() { echo -e "\033[1;34m===\033[0m $*"; }
die() { echo -e "\033[1;31m错误:\033[0m $*" >&2; exit 1; }

# ---------- [0] 依赖检查 ----------
log "[0/8] 依赖检查"
need_cmd() { command -v "$1" >/dev/null 2>&1 || die "缺少命令: $1"; }
need_cmd git; need_cmd patch; need_cmd tar; need_cmd zip; need_cmd zstd
if command -v clang >/dev/null 2>&1 && clang --version 2>/dev/null | grep -q "clang version 2[01]"; then
    :  # PATH 里已有 clang 21
elif [ -d /usr/lib/llvm21/bin ]; then
    export PATH=/usr/lib/llvm21/bin:$PATH
elif command -v clang-21 >/dev/null 2>&1; then
    export PATH="$(dirname "$(command -v clang-21)"):$PATH"
else
    die "需要 clang 21（Arch: sudo pacman -S clang21 lld21 llvm21）"
fi
clang --version | head -1
export LLVM=1 LLVM_IAS=1
# ★★★ 防 + 号：CONFIG_LOCALVERSION_AUTO=n 时 setlocalversion 会因 git 树非 clean 追加 +
export LOCALVERSION=""
export KBUILD_BUILD_USER="$BUILD_USER"
export KBUILD_BUILD_HOST="$BUILD_HOST"

# ---------- [1] 准备源码（三兄弟目录: src + sm8750-modules + sm8750-devicetrees）----------
log "[1/8] 准备源码 ($MODE 模式)"
if [ ! -d "$SRC_DIR/.git" ]; then
    die "缺少源码目录 $SRC_DIR，请先放好基线（或提供 KERNEL_SRC 环境变量后重试）"
fi
cd "$SRC_DIR"
git rev-parse HEAD | grep -q "$BASE_COMMIT" || die "基线不匹配: 期望 $BASE_COMMIT，实际 $(git rev-parse HEAD)"
[ -z "$(git status --porcelain)" ] || die "源码目录工作树不干净，请先清理"
# 兄弟目录：内核的符号链接指向它们（相对路径: ../sm8750-modules ../sm8750-devicetrees）
ensure_repo() { # $1=目标路径 $2=URL $3=期望提交 $4=标签 $5=本地镜像(可选)
    if [ ! -d "$1/.git" ]; then
        if [ -n "${5:-}" ] && [ -d "$5/.git" ]; then
            log "     从本地镜像克隆 $4（$5）"
            git clone --no-local "$5" "$1" || die "克隆 $4 失败"
        else
            log "     克隆 $4 → $1"
            git clone "$2" "$1" || die "克隆 $4 失败"
        fi
    fi
    cd "$1"
    [ "$(git rev-parse HEAD)" = "$3" ] || git checkout -q "$3" 2>/dev/null \
        || die "$4 不在期望提交 $3（实际 $(git rev-parse HEAD)）"
    cd "$SRC_DIR"
}
ensure_repo "$MODULES_DIR" "$REPO_BASE/Ace6-Development/android_kernel_oneplus_sm8750-modules" "$MODULES_COMMIT" "sm8750-modules" "${LOCAL_MODULES:-}"
ensure_repo "$DT_DIR"     "$REPO_BASE/LineageOS/android_kernel_oneplus_sm8750-devicetrees"   "$DT_COMMIT"      "sm8750-devicetrees" "${LOCAL_DT:-}"
# 关键符号链接目标验证（相对路径基于兄弟目录布局）
for t in "$SRC_DIR/drivers/base/kernelFwUpdate/Kconfig" \
         "$SRC_DIR/arch/arm64/boot/dts/vendor" \
         "$SRC_DIR/drivers/soc/oplus/boot" \
         "$SRC_DIR/include/soc/oplus/kernelFwUpdate.h"; do
    [ -e "$t" ] || die "符号链接目标缺失: $t（兄弟目录布局不对？）"
done
log "     ✓ 模块树/设备树就绪"

# ---------- [2] 应用主树补丁（SUSFS 主树 25 文件 + KSU 钩子 + lz4/zstd + Droidspaces + BBG 挂载 + CVE）----------
log "[2/8] 应用主树补丁 01_mainline.patch"
patch -p1 -F3 --batch -f < "$PATCH_MAIN" >/dev/null || die "主树补丁应用失败"

# ---------- [3] 解包 untracked 快照（新增文件 + KernelSU/.git 历史 + 符号链接）----------
log "[3/8] 解包快照（新增文件 + KernelSU 完整历史 + 符号链接）"
tar xzf "$SNAP_TAR" -C "$SRC_DIR"
[ -L "$SRC_DIR/drivers/kernelsu" ] || die "符号链接 drivers/kernelsu 缺失"
[ -L "$SRC_DIR/security/baseband-guard" ] || die "符号链接 security/baseband-guard 缺失"
[ -f "$SRC_DIR/fs/susfs.c" ] || die "fs/susfs.c 缺失"

# ---------- [4] KernelSU 准备 ----------
if [ "$MODE" = "clone" ]; then
    log "[4/8] clone 模式: 重拉 ReSukiSU 并应用适配补丁"
    [ -d KernelSU ] && rm -rf KernelSU drivers/kernelsu
    git clone "$KSU_REPO" KernelSU
    cd KernelSU && git checkout "$KSU_BRANCH" 2>/dev/null || true; cd ..
    ln -sfn ../KernelSU/kernel drivers/kernelsu
    (cd KernelSU && git apply --check ../patches/02_ksu.patch 2>/dev/null) \
        && (cd KernelSU && git apply ../patches/02_ksu.patch) \
        || echo "⚠  02_ksu.patch 未自动应用（KSU 版本可能已变），需人工适配" >&2
else
    log "[4/8] snapshot 模式: KernelSU 已随快照恢复（HEAD=$(cd KernelSU && git rev-parse --short HEAD)）"
fi
# 版本号验证: 30000 + rev-list --count + 700
KSU_COUNT=$(cd KernelSU && git rev-list --count HEAD)
KSU_VER=$((30000 + KSU_COUNT + 700))
log "     KSU 版本号: $KSU_VER ($KSU_COUNT 提交)"
[ "$KSU_VER" = "35046" ] || echo "⚠  KSU 版本 $KSU_VER ≠ 35046（快照被改动？）" >&2
# 钩子三连（setresuid/execveat/faccessat/sys_read/stat/reboot/input）已含在主树补丁内，
# 由 ReSukiSU manual_hook_check.mk + SUSFS inline_hook_check.mk 在 Kbuild 时强制校验

# ---------- [5] 配置 ----------
log "[5/8] 部署最终配置"
cp "$CFG_FINAL" .config
make LLVM=1 LLVM_IAS=1 ARCH=arm64 olddefconfig >/dev/null 2>&1 || die "olddefconfig 失败"
grep -q "^CONFIG_KSU=y" .config || die "CONFIG_KSU 未开启"
grep -q "^CONFIG_KSU_SUSFS=y" .config || die "CONFIG_KSU_SUSFS 未开启"
grep -q "^CONFIG_BBG=y" .config || die "CONFIG_BBG 未开启"
grep -q 'CONFIG_LOCALVERSION="-4k-gdc4c44f3ecc0-dirty"' .config || die "LOCALVERSION 未对齐"

# ---------- [6] 编译 ----------
log "[6/8] 编译 Image（-j$(nproc)）"
make LLVM=1 LLVM_IAS=1 ARCH=arm64 -j"$(nproc)" Image 2>&1 | tail -3
[ -f arch/arm64/boot/Image ] || die "编译未产出 Image"

# ---------- [7] 验证 ----------
log "[7/8] 验证产物"
IMAGE=arch/arm64/boot/Image
ls -la "$IMAGE"
# vermagic 权威源: utsrelease.h（compile.h 只有 COMPILE_BY/HOST，无版本串）
grep -q '6.6.139-4k-gdc4c44f3ecc0-dirty' include/generated/utsrelease.h || die "vermagic 未对齐"
grep -q "$BUILD_HOST" include/generated/compile.h || die "编译标签缺失"
strings "$IMAGE" | grep -q "Linux version 6.6.139" || die "Image 无版本串"
echo "     ✓ 版本串: $(grep UTS_RELEASE include/generated/utsrelease.h | sed 's/.*"//;s/".*//')"

# ---------- [8] 打包 AK3 ----------
log "[8/8] 打包 AnyKernel3 zip"
STAMP=$(date +%Y%m%d)
OUT_ZIP="$REPO_DIR/out/Kernel-Ace6-$BUILD_USER-$STAMP.zip" # out
mkdir -p "$REPO_DIR/out" "$REPO_DIR/work/pack"
rm -rf "$REPO_DIR/work/pack"/*
cp -a "$AK3_DIR"/. "$REPO_DIR/work/pack/"
cp "$IMAGE" "$REPO_DIR/work/pack/Image"
sed -i "s|kernel.string=.*|kernel.string=Ace6-$VER |" "$REPO_DIR/work/pack/anykernel.sh" 2>/dev/null || true
cd "$REPO_DIR/work/pack" && zip -r9 "$OUT_ZIP" . -x "*.git*" >/dev/null
log "完成: $OUT_ZIP"
ls -lh "$OUT_ZIP"
