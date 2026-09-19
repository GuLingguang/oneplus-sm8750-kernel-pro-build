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
# is not reproducible, so both sources are pinned below instead.
#
# Usage: scripts/install-pahole.sh [prefix]     (default work/_tools/pahole)
set -euo pipefail

DWARVES=v1.32
# The distribution package builds against libbpf master, and that is not
# reproducible, so this pins one master commit instead. It has to be a commit
# rather than a release tag: `struct btf_header` gained `layout_off`/`layout_len`
# after v1.7.0, which changes the BTF header from 24 to 32 bytes and with it the
# Image. A release tag would silently produce a different kernel from the same
# lock.
LIBBPF=f90a9c487d7542d91fa584b83b6a624a4fbeb341

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFIX="${1:-$ROOT/work/_tools/pahole}"
BUILD="${PAHOLE_BUILD_DIR:-$ROOT/work/_tmp/pahole-build}"

mkdir -p "$BUILD" "$PREFIX"
cd "$BUILD"

# Report the missing headers by name instead of letting cmake fail on a library.
# Debian/Ubuntu: libelf-dev libdw-dev zlib1g-dev libzstd-dev liblzma-dev libbz2-dev
# Arch:          libelf zlib zstd xz bzip2
missing=()
for header in libelf.h libdw.h zlib.h; do
  found=""
  for dir in /usr/include /usr/include/elfutils; do
    if [ -f "$dir/$header" ]; then found=1; break; fi
  done
  if [ -z "$found" ]; then missing+=("$header"); fi
done
if [ ${#missing[@]} -gt 0 ]; then
  echo "missing build headers: ${missing[*]}" >&2
  echo "install the libelf/libdw/zlib development packages first" >&2
  exit 1
fi

fetch() { # url file
  if [ ! -s "$2" ]; then
    curl -fsSL --retry 3 --retry-delay 3 -o "$2" "$1"
  fi
  echo "  $(basename "$2"): $(wc -c <"$2") bytes"
}

echo "== sources =="
fetch "https://github.com/acmel/dwarves/archive/refs/tags/$DWARVES.tar.gz" "dwarves-$DWARVES.tar.gz"
fetch "https://github.com/libbpf/libbpf/archive/$LIBBPF.tar.gz" "libbpf-$LIBBPF.tar.gz"

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
  -D CMAKE_INSTALL_RPATH="$PREFIX/lib" \
  -D CMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -D GIT_SUBMODULE=OFF \
  -D LIBBPF_EMBEDDED=ON >/dev/null
cmake --build build >/dev/null
cmake --install build >/dev/null

echo "== installed =="
echo "  prefix: $PREFIX"
echo "  pahole: $("$PREFIX/bin/pahole" --version)"
