# 设备端自有修改

> [English](CUSTOMIZATIONS.md) | **中文**

本文记录**设备本身**上的修改；内核构建仓库不负责这一层。内核侧的构建工作（补丁拆分、vermagic、ccache 等）属于构建仓库，不在本文重复。

---

## 1. ZRAM writeback：hybridswap backing

### 1.1 设备端修改

KSU 模块 `azram-backing` 是在锁定 Ace6 目标上把厂商 `hybridswap` 分区挂为 zram 写回 backing 的受保护交接模块。当前主 profile 已暴露可写的 `/sys/block/zram0/backing_dev`；v1.2 通过设备身份、分区用途、接口和 Scene 所有权检查后，已将 `/dev/block/sda13` 挂接为 backing。所有检查仍在破坏性转换前完成。

### 1.2 为什么选 hybridswap

- 1024MB 分区，`/dev/block/by-name/hybridswap`（块设备 `/dev/block/sda13`），厂商为混合交换预留——在这台 LOS 系 ROM 上**闲置**（fstab 无引用、无挂载、内核 config 无、厂商无使用记录；内容只有旧数据残留）
- 不占用 `/data`，也不依赖 loop——**44 个 loop 节点全被 Android apex 挂载占满**，文件+loop 方案在这台设备上不可行
- 写回量受 backing 大小限制：大 zram 配 1GB backing，写回上限 1GB——适用于不可压缩页和空闲页

### 1.3 模块与分工

`azram-backing` 只负责 backing 交接，不选择压缩算法、不决定 zram 大小，也不拥有 swapon。只有全部前置检查通过后才允许 reset；backing 设置失败时会尝试按记录的压缩算法、大小和 swap priority 恢复。zram 仍归 **Scene**（`scene_swap_controller`）管理，交接规则要求它的配置保持 `zram=false`、`zram_writeback=default`：

| 负责方 | 职责 |
|---|---|
| **azram-backing**（项目模块） | writeback 设备（backing = hybridswap） |
| **scene_swap_controller**（Scene） | zram：大小/算法/重建/swapon + backing 恢复 |
| **ZramWritebackBoost**（社区） | 写回调度（屏幕/前台/负载感知） |
| **tcp-config**（项目模块） | 运行时 TCP 拥塞控制与 qdisc（WebUI） |
| 内核 config | 默认压缩算法 lz4kd（项目 config 中的 choice） |

模块开机读取 `/data/swap_config.conf`。如果 Scene 被配置为主动重建 zram 或自行管理 writeback，本模块直接拒绝；不能把模块加载顺序当成同步机制。`ZramWritebackBoost` 只能作为写回统计/限额的下游消费者，不能 reset zram 或替换 backing。

### 1.4 内核约束（zram_drv.c）

- `backing_dev` 只能在 zram **未初始化**时配置——"Can't setup backing device for initialized device"
- `comp_algorithm` 初始化后锁定——必须在 `disksize` 之前设置
- 新 reset 的 zram 没有 swap 签名——必须先 `mkswap`，否则 swapon 报 EINVAL（Scene 的 startup.sh 也是这么做的）
- 当前主 profile 内核已暴露可写 `backing_dev`；受保护交接后设备显示 1GiB 的 `/dev/block/sda13` backing、6GiB zram、swap active，默认算法为 `lz4kd`
- kernel config 默认值和实际运行时算法是两回事；旧的 Inline profile 曾实测为 `[lzo-rle]`，主 profile 则使用锁定的 `lz4kd` 默认值

---

## 2. SELinux 权限例外（模块 `selinux_perf`）

这个模块是针对曾经观察到的 `vendor_hal_perf_default` 访问路径所加的
窄权限例外。`vendor_hal_perf_default` 是 source domain；`ksu` 和 `kernel`
是目标 **object type**，不是 domain。规则不等价于放开整个 `/proc`，也不应
被描述成无条件的性能提升。

**规则**（模块 `selinux_perf`，作者 GuLingguang）：

```
allow vendor_hal_perf_default ksu dir search
allow vendor_hal_perf_default kernel dir search
allow vendor_hal_perf_default ksu file { read open getattr }
allow vendor_hal_perf_default kernel file { read open getattr }
```

实际只授予目录 `search` 和文件 `read/open/getattr`，没有写入、创建、重标记
或执行权限。哪些路径带有 `ksu`/`kernel` 标签取决于 ROM 的 SELinux policy，
因此必须针对目标 policy 审查，不能概括成“修复 `/proc` 拒绝”。

**当前证据**：PLQ110 / OP6113L1 Android 16 测试机上，
`/data/adb/modules/selinux_perf/sepolicy.rule` 和 `module.prop` 均与工作树中
审查过的文件一致。SELinux 处于 Enforcing。受控停用/启用对照完成了两次
启动，每个阶段采样 5,000 条 logcat，均未发现
`vendor_hal_perf_default` 的 AVC。这不能证明性能收益，也不能证明该模块单独
消除了所有历史拒绝。详见
[`docs/execution-t21.md`](execution-t21.md) 和
[`docs/evidence/t21-selinux-perf.json`](evidence/t21-selinux-perf.json)。

---

## 3. TCP 拥塞控制 WebUI（模块 `tcp-config`）

KernelSU WebUI 页面（`webroot/` + `kernelsu` JS 库，esbuild 构建——源码在 `webui-src/`）提供三种算法和一个 qdisc：

- **cubic** —— Android 默认
- **bbr** —— BBR 建议配 fq，但 qdisc 是独立设置
- **内核编译默认** —— 实时读 `/proc/config.gz` 的 `CONFIG_DEFAULT_TCP_CONG`

qdisc（fq / fq_codel / pfifo_fast）**完全独立**：改算法不会动 qdisc，改 qdisc 也不会动算法（早期有个"auto 联动"会在算法变化时重写 qdisc，因语义混乱已移除）。WebUI 通过 `kernelsu.exec()` 调用共享的 `webroot/apply.sh`。旧的 nc/browser fallback 已主动移除：TCP socket 无法认证 Android 调用者，否则会把 root sysctl 操作暴露给不可信网络或本地进程。改动只影响新连接，保存到 `/data/adb/tcpcfg.state`（原子写入、权限 600），开机由 service.sh 重新应用（页面加载时也会恢复上次的选择）。这个内核上 `sysctl net.core.default_qdisc` 运行时有效（会更新 `default_qdisc_ops` 指针），但**没有编译期 config**——这棵树在 sch_generic.c 里硬编码了 `pfifo_fast_ops`，没用 `CONFIG_DEFAULT_NET_SCH`。

**设备边界**：`tcp-config v1.1` 已替换测试机上的旧 `v1.0`。未认证的 `*:8090` listener 已消失；直接应用 `cubic/fq` 和真实 WebUI 点击均通过，重启后状态恢复。一个只修复“内核默认值”显示解析的后续候选仍只保留在本地，未安装。

---

## 4. Scene：未修改（调查记录）

**发现**：Scene 模块 startup.sh 的 `set_zram()` 被 `[[ "$zram" == "true" ]] && [[ "$zram_size" != "" ]]` 挡住——Scene app 往 `/data/swap_config.conf` 写了 `comp_algorithm=lz4kd`，但**从没写 `zram`/`zram_size` 字段**，导致整个重建流程被跳过，init 的默认算法（旧内核 lzo-rle）一直生效。

**决策**：`/data/swap_config.conf` 的测试改动（`zram=true`/`zram_size`）已还原。Scene 是第三方模块，其配置不在本项目修改范围内。主 profile 内核现在提供 writeback 接口，因此 v1.2 可在不接管 Scene 大小、算法和 swapon 决策的前提下完成 backing 交接。设备已验证 6GiB zram、`lz4kd` 和 1GiB `hybridswap` backing 的活动状态。

---

## 5. NoActive 冻结名单：Google 相册必须白名单（2026-08-05）

**现象**：照片选择器（**相册与视频 Photos and videos** 权限 → **允许受限访问 Allow limited access** 模式）一直空白加载，偶尔正常；系统壁纸无法更换。

**排查**（`adb shell su -c "cat /dev/binderfs/binder_logs/transactions"`，本项目内核开了 binder debug）：
- media.module（`com.android.providers.media.module`）→ Google 相册（`com.google.android.apps.photos`）的同步事务 **46 分钟未返回**（`elapsed 2802649ms`）
- system_server 的 binder 线程被 GMS / 地图 / Gmail / Chrome / Nekogram 的 pending 同步事务占住（47–49 分钟），同一进程列表全部可对照 `ps -A -o pid=,args=` 解析
- 时间线与 NoActive 深度睡眠（`dozeType: locked`，锁屏 60 秒后挂起全部非白名单用户应用）完全吻合；深度睡眠退出后进程已恢复（`ps` 状态 `S`），但 pending 事务**永不消费**——binder 唤醒通知丢失

**根因**：Google 相册没进 NoActive 白名单。深度睡眠挂起相册后，挂起进程不再消费 binder 事务——media.module 对相册的调用永不返回，其 binder 线程池被占死，选择器查询永远排队；system_server 线程池同样被占 → 壁纸等系统 binder 调用卡死。「偶尔正常」= 挂起进程恰好被解冻、堆积事务侥幸被消费的间隙。

**解决**：Google 相册加入 NoActive 白名单（连同 GMS 等实际在用的 Google 应用）。

**结论**：冻结名单决定依赖服务是否会被挂起；Re:Kernel 钩子无法弥补名单错误。相册是照片选择器依赖的服务，被挂起后该链路无法完成。
