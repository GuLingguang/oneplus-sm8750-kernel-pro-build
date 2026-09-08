# T20：azram-backing 设备、分区与 zram 所有权审查

日期：2026-09-07。初始 T20 审查先在旧内核上拒绝了替换；随后主 profile
内核已经安装并暴露了 writeback 接口，完成了 v1.2 模块的受保护交接和一次
手动 writeback 验证。记录时所有变更只保留在本地，未上传或发布；后续仓库整理已在本地提交，仍未上传。

## 结果

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| 设备范围 | 已锁定 | `PLQ110 / OP6113L1 / Android 16` |
| backing 分区 | 已确认存在 | `/dev/block/by-name/hybridswap` → `/dev/block/sda13` |
| 分区冲突 | 当前未发现 | 未出现在 `/proc/mounts` 或 `/proc/swaps` |
| Scene 所有权 | 已确认 | Scene 脚本拥有 zram reset、compressor、disksize、backing 和 swapon |
| 当前 Scene 配置 | 兼容交接 | `zram=false`、`zram_writeback=default` |
| 当前内核 backing 接口 | 已通过 | `/sys/block/zram0/backing_dev` 存在且可写；已绑定 `/dev/block/sda13` |
| ZramWritebackBoost | 下游消费者 | 当前脚本调度 writeback/limit，不负责 reset 或设置 backing |
| azram-backing 前置检查 | 已实现 | 身份、配置、分区、挂载/swap 冲突、已有 backing 全部先检查 |
| 失败恢复 | 已实现 | 记录 compressor、大小和 swap priority；attach 失败尝试恢复 |
| 真机旧版处置 | 已完成 | 旧 `v1.0` 已本地备份并禁用；重启后 zram 仍 active，未执行 reset/swapoff |
| 真机 v1.2 替换/启动验证 | 已通过 | 主 profile 启动后模块已启用，backing 为 1 GiB，zram 为 6 GiB、默认算法 `lz4kd`，swap active |
| 手动 writeback | 已通过 | `echo idle > /sys/block/zram0/writeback` 返回 `rc=0`；`bd_stat` 已有非零记录 |

## 所有权边界

`azram-backing` 只负责一次性的 backing 交接；不选择算法、不决定大小、
不长期管理 swap。它要求 Scene 配置保持 `zram=false` 和
`zram_writeback=default`，否则直接拒绝运行。模块加载顺序不是同步协议，
不能单独作为安全依据。

## 当前限制

当前设备已经满足 writeback 前置条件；新版模块先检查所有 sysfs 接口，再执行
受保护的 backing 交接。当前只做了一次手动触发和启动后状态确认，没有把它扩大
为长时间压力、回滚或发布验收。EVDI/Droidspaces 容器生命周期和 Re:Kernel
用户空间协议仍是主 profile 的独立未完成验收项。
