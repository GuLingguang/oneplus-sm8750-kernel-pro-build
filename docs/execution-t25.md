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
