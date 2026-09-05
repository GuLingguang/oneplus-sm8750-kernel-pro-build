# Ace6 T06 执行记录：SUSFS Inline 6.6

日期：2026-09-05。此记录承接 `docs/execution-m1.md` 的 T01–T05
框架结果，范围只到 SUSFS Inline 的锁定源树准备和静态契约核验。

## 结果

| 项目 | 结果 | 边界 |
| --- | --- | --- |
| 官方 SUSFS 输入 | 完成 | 锁定 `gki-android15-6.6` / v2.3.0；文件和原始补丁已归档并固定 hash |
| ReSukiSU 集成 | 完成 | 使用候选提交的原生 `CONFIG_KSU_SUSFS` 分支和完整 `kernel/` 链接 |
| Ace6 6.6 适配 | 完成 | 官方补丁只调整目标树 `vma_data_pages()` 上下文，未改变语义 hunk |
| 锁定源树准备 | 完成 | 七个 lock step 全部 applied；准备阶段 manifest 已记录 |
| 接口/数据流 | 静态验证完成 | faccessat/stat 所有权、thread flags、zygote-next mount lookup 和跨 CU 签名均已核对 |
| 内核编译 / olddefconfig | 未执行 | 留给后续构建任务 |
| 真机和运行时 mount hiding | 未执行 | 留给 T26 |

## 锁定输入和顺序

| 来源 | 提交 | 用途 |
| --- | --- | --- |
| Ace6 kernel | `cb967c26c2c5689108fa28d3c3be2aba6ba71f5f` | 6.6.142 目标树 |
| modules | `7d5d39a539ddc2b53054e8fa7ae2b5890dccae54` | 独立模块源 |
| devicetrees | `ebb25e3526ad84cc5a1090a5a9242f33ff087bf2` | 设备树源 |
| ReSukiSU | `9d0ff6aea9e25fc7dd26f4643175a41f68375e5e` | KernelSU SUSFS Inline 实现 |
| SUSFS | `937215cb3a1b1f333d764c366c7a49972fa8e7a0` | 官方 6.6 补丁和源码输入 |

准备器按 lock 中的累计顺序执行：

1. 应用 `patches/split/07_compile_fixes.patch`。
2. 将 `drivers/kernelsu` 建为指向 `ReSukiSU/kernel` 的相对链接。
3. 加入内核 `drivers/Kconfig` 和 `drivers/Makefile` 的 ReSukiSU 源。
4. 复制官方 `fs/susfs.c`、`include/linux/susfs.h` 和
   `include/linux/susfs_def.h`。
5. 应用 `patches/integration/ace6-susfs-6.6.patch`。

最终链接目标是 `../../ReSukiSU/kernel`，不会把 ReSukiSU 文件复制成另一份
可能漂移的 adapter。官方 `KernelSU/10_enable_susfs_for_ksu.patch` 和旧的
`02_ksu.patch` 都没有进入此 profile。

## 契约核验

- `fs/open.c::do_faccessat` 使用 `getname_flags()` 得到
  `struct filename *`，将 `&fname` 传给 `ksu_handle_faccessat`，再执行
  `filename_lookup()` 和 `putname()`；错误指针和 retry 路径保持同一所有权序列。
- `fs/stat.c::vfs_statx` 与 `vfs_fstatat` 使用匹配的
  `ksu_handle_stat(..., struct filename **, ...)`，调用者保留 get/put 所有权。
- ReSukiSU `sucompat.h` / `sucompat.c` 在 `CONFIG_KSU_SUSFS` 分支的声明和
  定义均为 `struct filename **`。旧 `const char __user **` 仅存在于未选中的
  非 SUSFS/manual 兼容分支，不参与本 profile 的 VFS 调用。
- `setuid_hook.c` 设置 `no_su`、`umounted` 和
  `umounted_for_zygote_next`；`fs/namespace.c::__lookup_mnt` 读取后按
  `DEFAULT_KSU_MNT_ID` 过滤候选 mount。
- `TIF_PROC_UMOUNTED=33`、`TIF_PROC_NO_SU=34`、
  `TIF_PROC_UMOUNTED_FOR_ZYGOTE_NEXT=35` 及其访问器来自同一份官方 SUSFS
  `susfs_def.h`。

## 证据和出口

- 最终 `lock_id`：
  `81252695734e949099245701f9289696c04f93ec1f86c2b37c3cc103c20d8f37`。
- 最终源准备 `manifest_id`：
  `bc38224ff8f185a7ceeb60091aa80d2b09d4f1cebcb40f266538cc17a98583ac`。
- 五个外部提供目录均为锁定 HEAD、无 tracked/untracked/ignored 改动且无
  `skip-worktree` / `assume-unchanged` 项；准备后的 kernel `git diff --check`
  通过。
- `python3 -m unittest discover -s tests -v`：18 项通过，0 项失败。
- `python3 scripts/profile.py check --profile ace6-resukisu-susfs-inline-6.6`：
  `prepare_allowed=true`、`blockers=[]`、`build_implemented=false`、
  `runtime_status=not-tested`。

完整 hash、准备树 ID、步骤日志和静态断言见
`docs/evidence/t06-susfs-inline-preparation.json`；契约表见
`docs/susfs-inline-contract.md`。本阶段没有生成、发布或宣称可刷入的内核
产物。
