# Ace6 T17 execution record: KPM/KPatch-Next resource audit

Date: 2026-09-06. At the time of this record, all work remained local; no commit,
push or upload was made. Later repository cleanup was committed locally and was
not pushed.

## Result

| Item | Result | Boundary |
|---|---|---|
| KPatch-Next source identity | passed | clean source at the locked commit; version 0.13.5 revision 2 |
| Existing KPM-related binaries | rejected | provider binaries use the pre-2026 image format and are not interchangeable with the locked source |
| Current KPatch-Next binary build | blocked | ARM bare-metal compiler and Android NDK are not present |
| Profile lock integration | intentionally unchanged | every profile keeps `resources.kpm: null` |
| Image patch/package/runtime/device | not tested | no compatible KPM resource or full kernel Image is available |

## Source and format verification

The local `kpatch-next` source is clean at
`456744b29efb9989445463ab29e368fa59a103c4`, version `0.13.5` revision `2`.
Its current `kernel/include/preset.h` declares `KP_MAGIC` as `KP2026`; that
format change was introduced by `cc19c5ee72b05d5c3a2cfcf0fd3c3079ca81a5e4`.

The available `sukisu-patch` KPM bundle is tracked at
`547ae94bcaec53d030398f857950c64662043a5d`. Its `kpm/kpimg` begins with
`KP1158`, the pre-change format. Its Android `kptools` and `patch_android`
are also prebuilt AArch64 Android binaries; `patch_linux` is a host binary,
but its provenance is the same older bundle. The exact hashes are recorded
in `docs/evidence/t17-kpm.json`. These files were not added as a KPM lock
resource because doing so would assert compatibility that the format check
disproves.

## Build boundary

The pinned KPatch-Next build entry requires `aarch64-none-elf-gcc`, `ld`,
`as` and `objcopy` for `kpimg`, and an Android NDK for the Android `kpatch`
and `kptools` binaries. None of those target tools was available in the
unattended local environment. `zip` is also absent for packaging. The host's
clang 22 is not a substitute for the repository's locked AOSP Clang 21
kernel toolchain.

T17 therefore stops here. The next valid path is to provide the exact target
toolchains (or build a new, fully identified KPatch-Next resource from the
locked source), then establish compatibility with kernel commit
`cb967c26c2c5689108fa28d3c3be2aba6ba71f5f` before changing any profile lock.
