# Ace6 T14 execution record: compression and feature switches

Date: 2026-09-06. At the time of this record, all work remained local; no commit,
push or upload was made. Later repository cleanup was committed locally and was
not pushed.

## Result

| Item | Result | Boundary |
|---|---|---|
| LZ4 source identity | passed | upstream v1.10.0 commit and local kernel adaptations recorded |
| zstd source identity | passed | upstream v1.5.7 commit; 57-file backport verified non-empty |
| LZ4KD source identity | passed | 16 local algorithm/header/library files exactly match the pinned candidate |
| default compressor fallback | passed | LZ4KD off resolves to `lzo-rle`; LZ4KD on resolves to `lz4kd` |
| BBR false semantics | passed | `CONFIG_TCP_CONG_BBR` and `CONFIG_DEFAULT_BBR` are not set |
| Better network false semantics | passed | IP_SET/BPF stream parser/IPv6 NAT are not set |
| writeback false semantics | passed | writeback and its explicitly coupled tracking settings are not set |
| all zram algorithms | passed statically | nine backend names are present in the compiled zcomp object when enabled |
| representative object build | passed | 14 arm64 LLVM objects compile in the patch-04/all configuration |
| full Image/runtime/device | not tested | no full link, booted crypto round trip, writeback, BBR or device test |

## Source verification

The user-provided clones under `ace6/sources/` were checked at their locked
commits and were clean. The relevant compression sources are:

* `lz4-1.10.0`: `ebb370ca83af193212df4dcbadcc5d87bc0de2f0`
* `zstd-1.5.7`: `f8745da6ff1ad1e7bab384bd1f9d742439278e99`
* `sukisu-patch`: `547ae94bcaec53d030398f857950c64662043a5d`
* kernel: `cb967c26c2c5689108fa28d3c3be2aba6ba71f5f`

LZ4 and zstd were compared as upstream source versus their checked-in
kernel/freestanding adaptations; they are deliberately not reported as
byte-identical. Every LZ4KD file used by the build was byte-identical to the
candidate's `other/zram/lz4k/` files.

## Configuration verification

Two disposable cumulative trees were used: one with the required 07 + 02 +
03 sequence, and one with 07 + 02 + 03 + 04 plus the extra sources. Each
variant copied the final config, applied explicit toggle settings, and ran
`make ARCH=arm64 LLVM=1 olddefconfig`.

The full configuration table and hashes are in
`docs/evidence/t14-compression.json`. The patch-04/all case then compiled:

`crypto/{lz4,lz4hc,lz4k,lz4kd,zstd}.o`, `drivers/block/zram/zcomp.o`, both
LZ4 objects, both LZ4K objects, both LZ4KD objects and the zstd compressor and
decompressor module objects.

Only the kernel tree's pre-existing duplicate DTB recipe warnings appeared;
there were no compilation errors. No runtime or real-device claim follows
from this object-only result.
