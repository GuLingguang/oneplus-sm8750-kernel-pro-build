#!/usr/bin/env bash
# Build the pahole this repository pins, so a build does not inherit whichever
# pahole the host distribution happens to ship.
#
# Why this exists: pahole writes the kernel's BTF, and `CONFIG_PAHOLE_VERSION`
# records its version, so two hosts with different pahole versions produce
# different Images from the same lock. Recording the version in the manifest
# makes that difference visible; this script removes it.
#
# The build follows the Arch `pahole` package (dwarves 1.32, LIBBPF_EMBEDDED=ON,
# CMAKE_BUILD_TYPE=None). Arch builds against libbpf master at build time, which
# is not reproducible, so libbpf is pinned to a release tag instead.
#
# Usage: scripts/install-pahole.sh [prefix]     (default work/_tools/pahole)
set -euo pipefail

DWARVES=v1.32
LIBBPF=v1.7.0

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFIX="${1:-$ROOT/work/_tools/pahole}"
BUILD="${PAHOLE_BUILD_DIR:-$ROOT/work/_tmp/pahole-build}"

mkdir -p "$BUILD" "$PREFIX"
cd "$BUILD"

fetch() { # url file
  if [ ! -s "$2" ]; then
    curl -fsSL --retry 3 --retry-delay 3 -o "$2" "$1"
  fi
  echo "  $(basename "$2"): $(wc -c <"$2") bytes"
}

echo "== sources =="
fetch "https://github.com/acmel/dwarves/archive/refs/tags/$DWARVES.tar.gz" "dwarves-$DWARVES.tar.gz"
fetch "https://github.com/libbpf/libbpf/archive/refs/tags/$LIBBPF.tar.gz" "libbpf-$LIBBPF.tar.gz"

rm -rf "dwarves-${DWARVES#v}" "libbpf-${LIBBPF#v}"
tar xzf "dwarves-$DWARVES.tar.gz"
tar xzf "libbpf-$LIBBPF.tar.gz"

# dwarves carries libbpf as a git submodule; GIT_SUBMODULE=OFF plus a source
# tree in lib/bpf is what the distribution packages do.
echo "== libbpf -> dwarves/lib/bpf =="
rm -rf "dwarves-${DWARVES#v}/lib/bpf"
cp -r "libbpf-${LIBBPF#v}" "dwarves-${DWARVES#v}/lib/bpf"

echo "== build =="
rm -rf build
cmake -S "dwarves-${DWARVES#v}" -B build -G Ninja \
  -D CMAKE_BUILD_TYPE=None \
  -D CMAKE_INSTALL_PREFIX="$PREFIX" \
  -D CMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -D GIT_SUBMODULE=OFF \
  -D LIBBPF_EMBEDDED=ON >/dev/null
cmake --build build >/dev/null
cmake --install build >/dev/null

echo "== installed =="
echo "  prefix: $PREFIX"
echo "  pahole: $("$PREFIX/bin/pahole" --version)"
