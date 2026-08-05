#!/usr/bin/env bash
#
# Upstream drift check: does the current lineage-23.2 kernel tree still accept
# our 10 split patches?
#
# The whole reproducibility story rests on "upstream hasn't moved". This script
# makes that claim checkable instead of assumed:
#   - pulls the latest lineage-23.2 kernel source (zip, no git needed)
#   - dry-runs all 10 patches in workflow order (patch --dry-run touches nothing)
#   - exits 1 if any patch no longer applies
#
# Usage:
#   ./check_upstream.sh                 # download latest kernel, check everything
#   ./check_upstream.sh --local <tree>  # check an existing tree (fast, offline)
#   ./check_upstream.sh --ci            # CI mode: terse output, same exit code
#
# The workflow .github/workflows/upstream-check.yml wraps this weekly and opens
# an issue on failure. Local runs are the free path.

set -uo pipefail

KERNEL_REPO="Ace6-Development/android_kernel_oneplus_sm8750"
BRANCH="lineage-23.2"
WORK_DIR="${WORK_DIR:-work/upstream-check}"
CI_MODE=0
LOCAL_TREE=""

die() { echo "error: $*" >&2; exit 2; }
log() { [ "$CI_MODE" -eq 0 ] && echo "$*"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --ci) CI_MODE=1 ;;
    --local)
      [ $# -ge 2 ] || die "--local needs a tree path"
      LOCAL_TREE="$2"; shift
      [ -f "$LOCAL_TREE/Makefile" ] || die "not a kernel tree: $LOCAL_TREE"
      ;;
    -h|--help)
      grep '^#' "$0" | head -20
      exit 0
      ;;
    *) die "unknown arg: $1 (try --help)" ;;
  esac
  shift
done

# ---- 0. locate patches ----
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PATCH_DIR="$SCRIPT_DIR/patches/split"
PATCHES=("$PATCH_DIR"/*.patch)
PATCH_COUNT=${#PATCHES[@]}
[ "$PATCH_COUNT" -eq 10 ] || { log "warning: expected 10 split patches, found $PATCH_COUNT"; }

# ---- 1. source tree ----
if [ -n "$LOCAL_TREE" ]; then
  TREE="$LOCAL_TREE"
  log "using local tree: $TREE"
else
  mkdir -p "$WORK_DIR"
  cd "$WORK_DIR"
  log "fetching upstream commit..."
  COMMIT=$(curl -sL "https://api.github.com/repos/$KERNEL_REPO/commits/$BRANCH" \
    | grep -oE '"sha": "[0-9a-f]{40}"' | head -1 | grep -oE '[0-9a-f]{40}' || true)
  echo "upstream commit: ${COMMIT:-unknown}"
  log "downloading kernel zip ($BRANCH)..."
  curl -sL "https://github.com/$KERNEL_REPO/archive/refs/heads/$BRANCH.zip" -o kernel.zip \
    || die "download failed"
  rm -rf src && mkdir -p src
  unzip -q kernel.zip -d src && rm kernel.zip
  TREE="src/$(basename "$KERNEL_REPO")-$BRANCH"
fi
cd "$TREE"

# ---- 2. dry-run all patches in workflow order ----
FAILED=()
for p in "$PATCH_DIR"/[0-9][0-9]_*.patch; do
  name=$(basename "$p")
  if patch -p1 -F3 --batch --dry-run -f < "$p" > /dev/null 2>&1; then
    log "  ok   $name"
  else
    echo "  FAIL $name"
    FAILED+=("$name")
  fi
done

# ---- 3. report ----
OK=$((PATCH_COUNT - ${#FAILED[@]}))
if [ "${#FAILED[@]}" -eq 0 ]; then
  echo "result: $OK/$PATCH_COUNT patches apply cleanly"
  exit 0
else
  echo "result: ${#FAILED[@]}/$PATCH_COUNT patches FAILED:"
  printf '  - %s\n' "${FAILED[@]}"
  echo "hint: the tree moved. Review the failed hunks before the next build."
  exit 1
fi
