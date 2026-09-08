# Ace6 T08 执行记录：Baseband Guard

日期：2026-09-06。范围是锁定 BBG 来源、修复 dentry/保护谓词及其相关
空值路径，并在隔离的 Ace6 6.6 树上完成对象级检查；不包含完整内核、刷机、
真机或破坏性分区测试。

## 结果

| 项目 | 结果 | 边界 |
| --- | --- | --- |
| 来源/fork | 已锁定 | `cctv18/Baseband-guard@a5b57f15`；镜像只改变传输 |
| dentry 条件反转 | 已修复 | 有效 dentry 才进入 inode/target 检查，NULL/ERR 提前放行 |
| rename / setattr | 对象级已覆盖 | 未信任进程命中受保护 block device 时拒绝；可信进程放行 |
| symlink 路径 | 对象级已覆盖 | 绝对链接解析到受保护 block device 时拒绝；普通/允许目标放行 |
| LSM / Kconfig | 已检查 | `CONFIG_BBG=y` 且 `CONFIG_LSM` 含 `baseband_guard` |
| BBG 对象编译 | 通过 | 6.6 隔离树的 `baseband_guard.o`、`tracing.o`；非完整 kernel build |
| 决策模型 | 11/11 通过 | 9 个 dentry case + 2 个可信度 gate |
| runtime / release | 未测试 / 禁止 | 不使用真实基带或分区做破坏性试验 |

## 本地改动

- `baseband_guard.c`：修正 `IS_ERR_OR_NULL()` 方向；把 block-device
  判断变为真正的保护谓词；补充 inode、`i_op`、`i_sb`、rename dentry
  的空值保护；统一 symlink target 的资源释放；为 rename 补可信进程旁路。
- `Makefile`：停止从 vendored 目录向上误探测 kernel Git 仓库，也不在构建
  时 fetch；固定打印的 fork URL 和完整来源提交，避免错误身份与网络依赖。

## 结论

T08 的源码/对象级门槛已完成，但 BBG 仍不是 runtime-accepted 或可发布
功能。其实际设备覆盖、LSM 顺序、真实写入/rename/setattr/ioctl 行为留给
后续构建与真机任务；当前所有修改都保留在本地工作树。

详细规则见 `docs/baseband-guard-rules.md`，机器证据见
`docs/evidence/t08-baseband-guard.json`。
