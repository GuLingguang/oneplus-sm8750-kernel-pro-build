# T25：分层构建与复现记录

日期：2026-09-06。记录时所有构建和检查均在本地完成，未提交、上传或发布产物。后续仓库整理已在本地提交，仍未上传。

## 结果

| 类别 | 结果 | 说明 |
| --- | --- | --- |
| 非阻塞 profile 完整构建 | 5/5 通过 | 每个 profile 均使用锁定源码、30 个并行任务、独立 work/out 目录 |
| AK3 包完整性 | 5/5 通过 | 所有 ZIP 通过 `zip -T` |
| 构建前负例 | 3/3 正确拒绝 | Droidspaces extend 受 T11 阻塞；Re:Kernel 受 T13/T26 阻塞 |
| 最终 Image 身份 | 5/5 通过 | builder 检查 Image banner 与 `kernel.release` 一致 |
| 项目测试 | 通过 | `python3 -m unittest discover -s tests -q`：26/26 |
| 工作区检查 | 通过 | `git diff --check` |
| CI/本地同锁对照 | 未执行 | 记录时未上传或触发 CI；本地 commit 不改变该结论 |
| 字节完全可复现 | 未宣称 | 构建时间等影响字节的输入尚未固定并进行二次构建对照 |

## 已构建 profile

| Profile | Config ID | Lock ID | Image SHA256 | AK3 SHA256 |
| --- | --- | --- | --- | --- |
| `ace6-minimal-6.6` | `b0f963f43d5a37f491044f5bcb0901f3864286e9cc006a3ee728692340504da7` | `da327f6c4191249654f2e39ce3b29e53e1515e112a7c2c57efbf29e780bac52f` | `989b9f7b0705b5d801f80b4a214f73cd22205e19bb6434bd3eb1f1d26069c4f9` | `d9a93a69c06e2b583edf768394e06cadfd5e2add356521555e6bd7c60ef15628` |
| `ace6-resukisu-manual-6.6` | `fb177f1e62e19b1df2e18625014d7ce5eaf7002293494bd9bad3a3496be72525` | `68f555494985d3907ff2f8524326e54a6b8abce7466b4eb712604393790a49d5` | `56bfe16ab90b858ab817e93a4682ed173e0dd0c15456012cbb38be78b70b153a` | `c73185fc98085bd27aabb84ba7a5bc10152d581a160de94dd127672d8bacecac` |
| `ace6-resukisu-susfs-inline-6.6` | `8f27df126bda1f578127ee69e8273f1f9b0c08bfda9e0c3e083db2f5f906244e` | `e03aff8df39f8aab50e5c5cb74e0e2dacea28849a9590d1078cfd26380280a90` | `252fd976f9df48a1eeea3bf8a843cb0b1ab0e49eb4afcac32e207a1923d0d36a` | `e6fbc2e0b11357a1bd7fcc8aba631b7fa8c25fc3acdcc46f68b773a612c64233` |
| `ace6-droidspaces-standard-6.6` | `22d5db5d559aa3d18463328990dc2833543e430a67c48372000ac083d821ade2` | `3b215a48a94426371410a240d81f500c593b450aec738f26b951434f50277470` | `c765351035c1de81fb4b3d3a8e648efd0e1d40ce2c613df8b712244fd15eb7ce` | `7b7ee0731a1bb20daf13590cbcfa4b2d8843b946735fe4f8465b8ec40f4a63fb` |
| `ace6-droidspaces-resukisu-standard-6.6` | `172f25ac7bf71faab71b742daa96bc493364d0b5b4bbc09a90304a431c2ae330` | `3f0d027b535ee641a17bc46e00da6f672daf4d8d383e0f7fbfa6d7a35f0e4153` | `21aa733d51d7aff462fc8641e4aa5735941e2eeba4d5640bfd5a5b15f36e90ed` | `383cd67bccf49468f5a55595b51bfd63929e44052a6789f9e7e34a39f5ddb266` |

## 保持阻塞的 profile

- `ace6-droidspaces-extend-6.6`：T11 的 EVDI ABI、virtual HCI、systemd-coredump 和设备 userspace 条件未锁定。
- `ace6-droidspaces-resukisu-extend-6.6`：同上。
- `ace6-rekernel-experimental`：T13/T26 的 NoActive userspace 协议和运行时验证未完成。

## 边界

本记录完成构建组合和产物级验收。T26 真机功能验证另行记录，profile 之间也未因此获得同一设备上的运行保证。当前仍保持 `release_allowed=false`。

## Follow-up 2026-09-11 — CI/local comparison on one lock

The first table recorded `ci_local_comparison` as not run. It has now been
performed for `ace6-minimal-6.6` against Run `34310782005`, which built that
profile from one lock (`778e65a45b1a3bff5a1e5eb284aa95ee17a0bf09bdb636782cf68bc45b62f62f`
on both sides at build time).

`scripts/build.py` is itself a hashed local input, and it was edited again
after these builds. Every refresh moves the lock digest, so the checked-in lock
is now `9e324048…` even though `sources`, `steps`, `resources`, `blockers` and
every other `local_files` entry are unchanged. The lock IDs recorded below are
therefore build-time values, and the kernel inputs they describe are still the
checked-in ones. A later build would need a fresh comparison against the
current digest.

Both builds do share one lock, one profile and one feature lock. They do not
produce the same bytes. Extracting the embedded configuration from each AK3
package with the kernel tree's own `scripts/extract-ikconfig` shows why:

| Input | Local | CI |
| --- | --- | --- |
| `CONFIG_PAHOLE_VERSION` | `131` | `125` |
| embedded build stamp | `Fri Sep 11 12:22:03 CST 2026` | `Wed Sep  9 04:40:27 UTC 2026` |
| `ccache_debug` | `false` | `true` |

Every other configuration line is identical across all 8,757 of them. The
pahole difference is a host package difference: this host has `v1.31`, and the
runner host setup installs `1.25-0ubuntu3`. It changes the recorded version and
the generated BTF, which is enough to move the Image size by 65,536 bytes.

The remaining differences do not reach the kernel: `ccache_debug` only changes
`config_id`, and the runner locale only changes the wording of patch logs.

| Item | Local | CI |
| --- | --- | --- |
| `lock_id` (build time) | `778e65a4…` | `778e65a4…` (same) |
| `config_id` | `b0f963f4…` | `5f406619…` |
| Image size | 36,874,752 | 36,940,288 |
| Image SHA-256 | `28012be53279e770896f72674e40a592605ad4b228d02d6df6d325e47768907a` | `f73aa04aa1b12da3198494ae8e294978e6aa8923748eec7026994d89591109d6` |
| AK3 SHA-256 | `d1d0dc224dbc7a405c44677da6c07c7d31589d5f99fd…` | `20a32b85f28e37917caca3603763a37236ca18c16c19af…` |

Machine-readable detail is in
`docs/evidence/t25-ci-local-same-lock-20260911.json`.

The conclusion matches what the locks already state: `byte_identical_build`
stays false, and this evidence does not change it. Reaching byte-identical
builds now has a concrete, bounded prerequisite — pin one pahole version and
fix `KBUILD_BUILD_TIMESTAMP`. The README used to claim the timestamp was
already fixed through faketime; nothing called it, and the claim has been
replaced in this change by the behaviour described here.

This follow-up covers one profile and changes no lock, artifact, or release
state.

## Follow-up 2026-09-11 — two builds from one lock

The comparison above showed that the embedded build stamp came from the wall
clock, so the same lock could not produce the same bytes even on one host.
`scripts/build.py` now resolves an empty `build_time` to the locked kernel
commit's committer date and always sets `KBUILD_BUILD_TIMESTAMP`, and it records
`toolchain.pahole` and `build.build_timestamp_source`.

Two full builds of `ace6-minimal-6.6` were then run from the refreshed lock
`b8b89c932dcb80660baf3bda32b2204d35b971fe03dc42e5f3e32e3b85edfb65`, each into a
fresh `work/` and `out/` directory. As above, that ID is the build-time value;
`scripts/build.py` changed afterwards, which moved the checked-in digest
without changing any kernel input.

| Item | Build A | Build B | Result |
| --- | --- | --- | --- |
| `lock_id` (build time) / `config_id` | `b8b89c93…` / `b0f963f4…` | same | one lock |
| `build_timestamp` | `Tue Aug 18 16:57:28 UTC 2026` | same | deterministic |
| `build_timestamp_source` | `locked-commit-date` | same | derived |
| `UTS_VERSION` | `#1 SMP PREEMPT Tue Aug 18 16:57:28 UTC 2026` | same | deterministic |
| Image size | 36,874,752 | 36,874,752 | equal |
| Image SHA-256 | `e67ace27…` | differs | 1,128 bytes differ |
| AK3 SHA-256 | `906b6a4f…` | differs | zip entry times |
| `toolchain.pahole` | `v1.31` | same | recorded |

The build stamp is now reproducible. The Image is not yet byte-identical: 1,128
of 36,874,752 bytes differ, in six regions, and all of them belong to the
module signing material. `CONFIG_MODULE_SIG=y` with
`CONFIG_MODULE_SIG_KEY="certs/signing_key.pem"` makes the kernel generate a
fresh random RSA key and a self-signed X.509 certificate on every build. The
certificate subject is `Build time autogenerated kernel key`, and its validity
is taken from the generation moment, so it changes even when every other input
is fixed. The AK3 archive then differs again because `zip` records each entry's
modification time.

That leaves one open item rather than an unknown: supplying a fixed signing key
and certificate would make the Image reproducible, and normalising the packaged
entry times would carry that through to the archive. Choosing a signing key is
a key-management decision, so it is not made here. Until it is, the comparison
that remains meaningful between two builds is the Image excluding the signing
material.

The packaging half is now done. `prepare_package` stamps every entry from the
locked commit date and runs `zip` with `TZ=UTC`, so the archive no longer
carries the time it happened to be written. Two packaging runs over one Image
produce the same file:

| Run | AK3 SHA-256 | Size |
| --- | --- | --- |
| first | `68262b5fb5d131e8b19d8b95a46cc58f…` | 18,498,758 |
| second | `68262b5fb5d131e8b19d8b95a46cc58f…` | 18,498,758 |

The same comparison previously differed by four bytes. With the build stamp and
the packaging times both fixed, the module signing key is the only remaining
input that separates two builds from one lock.

Machine-readable detail is in
`docs/evidence/t25-two-build-reproducibility-20260911.json`.

## Follow-up 2026-09-11 — signing key, artifact date and build path

Three further inputs were removed from the difference between two builds of one
lock. Each was found by rebuilding twice and reading where the bytes still
disagreed.

| Change | Image bytes differing |
| --- | --- |
| starting point | 1,128 |
| checked-in module signing key | 60 |
| artifact name date from the locked commit | 60 |
| `-ffile-prefix-map` for the repository and work directory | 60 |

The remaining 60 bytes are three 20-byte build-id notes. Everything else in the
Image is identical. `--build-id=sha1` hashes the whole vmlinux, and the DWARF
still varies in a way the prefix map does not normalise, so the note moves while
the allocated content does not.

What is now verified:

- `CONFIG_MODULE_SIG_KEY` points at `keys/module-signing.pem`, no key is
  generated, and `certs/signing_key.x509` is identical in both builds;
- the artifact name is `Kernel-Ace6-Lingguang-20260818.zip` in both, taken from
  the locked commit rather than the build day;
- `DW_AT_comp_dir` is `/ace6/work/src`, and neither build directory name occurs
  anywhere in the vmlinux.

That note closed by saying the last 60 bytes would need the build id pinned or
dropped. The following section supersedes it.

## Follow-up 2026-09-16 — byte-identical builds

The last 60 bytes came from two more flag channels that never saw the prefix
map, so the debug information was still not deterministic and the build id,
which hashes it, moved with it. Each was found by rebuilding twice and reading
where the sections still disagreed.

| Change | Image bytes differing |
| --- | --- |
| starting point | 1,128 |
| checked-in module signing key | 60 |
| artifact name date from the locked commit | 60 |
| `-ffile-prefix-map` on `KCFLAGS` | 40 |
| the same maps on `KAFLAGS` (`.S` files) | 40 |
| the same maps on `KCPPFLAGS_COMPAT` (32-bit compat vDSO) | **0** |

Two builds of `ace6-minimal-6.6` from one lock now agree exactly:

| Item | Build A | Build B |
| --- | --- | --- |
| Image SHA-256 | `7e4dd0bb023904b76208b6845958747e4504a53675be53d524d1e75837a83d07` | identical |
| Image size | 36,743,680 | identical |
| AK3 SHA-256 | `ad27c54f132c41c6d99408c4a7f2940b972342adacd19f0072751ba9d25f7caf` | identical |
| `UTS_VERSION` | `#1 SMP PREEMPT Tue Aug 18 16:57:28 UTC 2026` | identical |
| artifact name | `Kernel-Ace6-Lingguang-20260818.zip` | identical |
| `lock_id` | one lock | identical |

Only `build.started_utc` and the `manifest_id` derived from it differ, and both
describe when the build ran rather than what it produced.

The build id was left in place. Pinning or dropping it would have closed the
byte count in one line while removing a debugging aid, so the fix was to make
the debug information deterministic instead.

Two things bound this result. It covers one profile on one host; the other eight
profiles have not been rebuilt this way. And a lock is only a byte-identical
claim across hosts with the same pahole version, because pahole changes
`CONFIG_PAHOLE_VERSION` and the generated BTF.

A measurement note for anyone repeating it: with
`CONFIG_DEBUG_INFO_COMPRESSED_ZSTD=y` the compressed debug sections avalanche,
so `cmp` on the compressed vmlinux reported 38,851,826 differing bytes while the
underlying difference was a single path string. Decompress the sections first,
or compare per-section hashes, and do not use byte counts from the compressed
file.

Machine-readable detail is in
`docs/evidence/t25-byte-identical-20260916.json`.

## Follow-up 2026-09-18 — all nine profiles, two builds each

The result above covered one profile and said so: the other eight had not been
rebuilt this way. All nine have now been built twice from one lock, each build
into a fresh `work/` and `out/` directory, with the locked sources cloned
locally from pinned checkouts so the build itself touches no network.

| Profile | AK3 SHA-256 | Image SHA-256 | Image size | AK3 size |
| --- | --- | --- | --- | --- |
| `ace6-droidspaces-extend-6.6` | `a3c1cf8d5a67…` | `59824997e634…` | 37,210,624 | 18,648,161 |
| `ace6-droidspaces-resukisu-extend-6.6` | `ee5251597590…` | `564c773029e0…` | 37,411,328 | 18,728,446 |
| `ace6-droidspaces-resukisu-standard-6.6` | `84c88c12f2a2…` | `6c6f82712663…` | 37,276,160 | 18,706,719 |
| `ace6-droidspaces-standard-6.6` | `c0371b0eee99…` | `5705dfe85f6f…` | 37,079,552 | 18,627,254 |
| `ace6-main-release-compat-6.6` | `a7d7a495ed9c…` | `2607e2666aa7…` | 37,411,328 | 18,745,011 |
| `ace6-minimal-6.6` | `ad27c54f132c…` | `7e4dd0bb0239…` | 36,743,680 | 18,437,868 |
| `ace6-rekernel-experimental` | `e72ca551922d…` | `8407c6bc05ae…` | 36,874,752 | 18,521,793 |
| `ace6-resukisu-manual-6.6` | `e0e38a05aa54…` | `56aaf60ba332…` | 36,874,752 | 18,517,784 |
| `ace6-resukisu-susfs-inline-6.6` | `81d799e7a627…` | `1921d331655f…` | 36,878,848 | 18,529,853 |

Both builds of each profile carry the same `lock_id`, `config_id`,
`build_timestamp`, build-stamp source and recorded pahole version. The only
fields that move between them are `build.started_utc` and the `manifest_id`
derived from it, exactly as in the single-profile result above.

`ace6-minimal-6.6` reproduces its 2026-09-16 artifact byte for byte
(`7e4dd0bb…`, `ad27c54f…`), so the property also held across the twelve commits
that landed in between. Those commits changed packaging and stamp inputs, not
kernel inputs.

Three of the nine were listed as blocked in the tables above. They build, and
they also built in the 2026-09-09 CI run that compiled all nine. The blockers
recorded for them are acceptance conditions — the EVDI ABI and the NoActive
userspace protocol — not build-time refusals. Nothing here changes those
conditions, and `release_allowed` stays false for every profile.

The cross-host bound from 2026-09-16 is unaffected and still applies: a lock is
a byte-identical claim across hosts only when both use the same pahole version.
This host records `v1.32`; the CI runner installs `1.25`, so the same lock does
not produce the same bytes there. Closing that gap needs one pinned pahole
version on both sides, and it is not done here.

Machine-readable detail is in
`docs/evidence/t25-nine-profile-reproducibility-20260918.json`.

## Follow-up 2026-09-19 — the same bytes on another host

The section above left one bound: a lock was a byte-identical claim on one host,
with the note that pahole had to match for it to hold across hosts. Two inputs
were still free. Both are now pinned.

| Input | Before | Now |
| --- | --- | --- |
| pahole | whatever the host installs — `v1.32` here, `1.25` on the runner | `scripts/install-pahole.sh` builds dwarves 1.32 with the distribution's options and a pinned libbpf |
| AK3 entry order | `zip -r` walked the directory in readdir order, so ext4 and btrfs packed the same Image into different archives | `prepare_package` hands zip an explicit sorted entry list |

The libbpf pin has to be a commit rather than a release tag. `struct btf_header`
gained `layout_off` and `layout_len` after v1.7.0, so a build against v1.7.0
writes a 24-byte BTF header where the distribution's writes 32. Everything else
in that comparison matched — same configuration, same size, same type and string
section lengths — and those eight bytes still moved every byte after the BTF
section.

`ace6-minimal-6.6`, `ace6-resukisu-susfs-inline-6.6` and
`ace6-main-release-compat-6.6` were built on the runner (run 35442823271,
`main` at `5f9daf8`) and twice on this host, all from one lock per profile. The
archives agree exactly:

| Profile | AK3 SHA-256 | Image SHA-256 | AK3 size |
| --- | --- | --- | --- |
| `ace6-droidspaces-extend-6.6` | `74a3ddf2992d…` | `59824997e634…` | 18,647,225 |
| `ace6-droidspaces-resukisu-extend-6.6` | `735bdbc0ea46…` | `d772a7c6091a…` | 18,727,687 |
| `ace6-droidspaces-resukisu-standard-6.6` | `0a9800c88243…` | `df96277f2aaa…` | 18,706,132 |
| `ace6-droidspaces-standard-6.6` | `6d47197753ee…` | `5705dfe85f6f…` | 18,626,318 |
| `ace6-main-release-compat-6.6` | `612beb313f20…` | `cc4de61fd718…` | 18,744,032 |
| `ace6-minimal-6.6` | `fbb2ce482e81…` | `7e4dd0bb0239…` | 18,436,932 |
| `ace6-rekernel-experimental` | `7aea6f2ba997…` | `a8ddc628a634…` | 18,521,440 |
| `ace6-resukisu-manual-6.6` | `e970c92edc56…` | `78bdf0980ebd…` | 18,516,931 |
| `ace6-resukisu-susfs-inline-6.6` | `38d4636568cb…` | `3effccf368bb…` | 18,529,397 |

Machine-readable detail is in
`docs/evidence/t25-reproducibility-and-cross-host-20260919.json`, which replaces
`t25-nine-profile-reproducibility-20260918.json`; that file is removed because
its AK3 hashes predate the archive order fix, and its ReSukiSU profiles were
built from a clone without tags.

One input does not show up in the numbers but changes them. ReSukiSU's
`Kernel/Kbuild` takes its version name from `git describe --abbrev=0 --tags` and
falls back to a hardcoded string when the repository carries no tags, so a build
from a tag-less clone embeds `v4.1.0` where a normal build embeds `v4.2.0-rc1`
and produces a different kernel. The clones this repository prepares fetch the
tags the remote advertises; `--source NAME=PATH` bypasses that and has to be
given a checkout that carries them too.

The first pass covered the three profiles a `scope=compile` run builds. The
`scope=full` run 35448366308 then built all nine on the runner, and every one of
them matches this host as well — so the table above is nine for nine on both
counts: each profile agrees with its own rebuild, and with the runner's.

Two limits stand. This covers one host and one runner, and none of it says
anything about device behaviour; `release_allowed` stays false.
