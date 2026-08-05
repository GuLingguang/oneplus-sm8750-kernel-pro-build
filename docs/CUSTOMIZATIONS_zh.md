# 设备端自有修改

> [English](CUSTOMIZATIONS.md) | **中文**

我们在**设备本身**上做的修改——内核构建仓库不负责的这一层。内核侧的构建工作（补丁拆分、vermagic、ccache 等）属于构建仓库，不在本文重复。

---

## 1. ZRAM writeback：hybridswap backing

### 1.1 做了什么

通过 KSU 模块 `azram-backing`（在 `modules/`）在每次开机时把厂商的 `hybridswap` 分区挂为 zram 的写回 backing 设备。

### 1.2 为什么选 hybridswap

- 1024MB 分区，`/dev/block/by-name/hybridswap`（块设备 `/dev/block/sda13`），厂商为混合交换预留——在这台 LOS 系 ROM 上**闲置**（fstab 无引用、无挂载、内核 config 无、厂商无使用记录；内容只有旧数据残留）
- 零 `/data` 空间占用、零 loop 依赖——**44 个 loop 节点全被 Android apex 挂载占满**，文件+loop 方案在这台设备上不可行
- 写回量受 backing 大小限制：大 zram 配 1GB backing，写回上限 1GB——覆盖不可压缩/空闲页的尾巴足够

### 1.3 模块与分工

`azram-backing` 只做一件事：`swapoff → reset → 配 backing`，然后停。zram 本身归 **Scene**（`scene_swap_controller`）管——它负责重建设备（大小、算法、swapon），其"恢复 writeback"分支会重新接上我们配的 backing（它在自己的 reset **之前**读 `backing_dev`）——Scene 本来就是按这个方式设计的：

| 负责方 | 职责 |
|---|---|
| **azram-backing**（我们） | writeback 设备（backing = hybridswap），仅此而已 |
| **scene_swap_controller**（Scene） | zram：大小/算法/重建/swapon + backing 恢复 |
| **ZramWritebackBoost**（社区） | 写回调度（屏幕/前台/负载感知） |
| **tcp-config**（我们） | 运行时 TCP 拥塞控制与 qdisc（WebUI） |
| 内核 config | 默认压缩算法 lz4kd（我们的 config 里翻的 choice） |

`a` 前缀让我们的模块最先执行，保证 backing 在 Scene 重建之前就位；Scene 的配置文件不碰。

### 1.4 踩过的内核约束（zram_drv.c）

- `backing_dev` 只能在 zram **未初始化**时配置——"Can't setup backing device for initialized device"
- `comp_algorithm` 初始化后锁定——必须在 `disksize` 之前设置
- 新 reset 的 zram 没有 swap 签名——必须先 `mkswap`，否则 swapon 报 EINVAL（Scene 的 startup.sh 也是这么做的）
- 默认算法：构建 config 里把 `CONFIG_ZRAM_DEF_COMP` 从 LZORLE 翻到 LZ4KD，init 建出的 zram 直接就是 lz4kd，零运行时配置

---

## 2. SELinux 静音（模块 `selinux_perf`）

**问题**：`vendor_hal_perf_default`（性能 HAL）开机扫描 `/proc` 时反复触发对 `ksu` / `kernel` 域的 `avc: denied`——每次开机日志刷屏。

**修复**（模块 `selinux_perf`，作者 GuLingguang）：

```
allow vendor_hal_perf_default ksu dir search
allow vendor_hal_perf_default kernel dir search
allow vendor_hal_perf_default ksu file { read open getattr }
allow vendor_hal_perf_default kernel file { read open getattr }
```

**验证**：模块安装后 dmesg 尾部已无 perf-HAL 拒绝记录（只剩少量无关的低频记录）。

---

## 3. TCP 拥塞控制 WebUI（模块 `tcp-config`）

KernelSU WebUI 页面（`webroot/` + `kernelsu` JS 库，esbuild 构建——源码在 `webui-src/`）提供三种算法和一个 qdisc：

- **cubic** —— Android 默认
- **bbr** —— BBR 建议配 fq，但 qdisc 是独立设置
- **内核编译默认** —— 实时读 `/proc/config.gz` 的 `CONFIG_DEFAULT_TCP_CONG`

qdisc（fq / fq_codel / pfifo_fast）**完全独立**：改算法不会动 qdisc，改 qdisc 也不会动算法（早期有个"auto 联动"会在算法变化时重写 qdisc，因语义混乱已移除）。WebUI 与浏览器 fallback 通道共用同一个核心脚本（`webroot/apply.sh`）：WebUI 通过 `kernelsu.exec()` 调用它，fallback 通道是 `busybox nc -lk` 在 `:8090` 的迷你 HTTP 服务器（KSU 的 busybox 没有 httpd CGI、toybox 根本没有 httpd，所以用 `nc -lk -p 8090 -e handler.sh` 裸实现；页面在没有 `ksu` bridge 的环境回退到 `fetch()`）。改动只影响新连接，保存到 `/data/adb/tcpcfg.state`，开机由 service.sh 重新应用（页面加载时也会恢复上次的选择）。这个内核上 `sysctl net.core.default_qdisc` 运行时有效（会更新 `default_qdisc_ops` 指针），但**没有编译期 config**——这棵树在 sch_generic.c 里硬编码了 `pfifo_fast_ops`，没用 `CONFIG_DEFAULT_NET_SCH`。

---

## 4. Scene：不碰（调查记录）

**发现**：Scene 模块 startup.sh 的 `set_zram()` 被 `[[ "$zram" == "true" ]] && [[ "$zram_size" != "" ]]` 挡住——Scene app 往 `/data/swap_config.conf` 写了 `comp_algorithm=lz4kd`，但**从没写 `zram`/`zram_size` 字段**，导致整个重建流程被跳过，init 的默认算法（旧内核 lzo-rle）一直生效。

**决策**：我们考虑过修补 `/data/swap_config.conf`（补 `zram=true`/`zram_size`），测试后**已还原**——Scene 是第三方模块，我们不修改它的配置。writeback 由 `azram-backing` 自足实现（见第 1 节），Scene 的 zram 功能保持关闭，文件保持 Scene app 写入的原样（`comp_algorithm=lz4kd` 留着，只是 Scene 的 zram 开关关闭时用不上）。

---

## 5. NoActive 冻结名单：Google 相册必须白名单（2026-08-05）

**现象**：照片选择器（**相册与视频 Photos and videos** 权限 → **允许受限访问 Allow limited access** 模式）一直空白加载，偶尔正常；系统壁纸无法更换。

**排查**（`adb shell su -c "cat /dev/binderfs/binder_logs/transactions"`，本项目内核开了 binder debug）：
- media.module（`com.android.providers.media.module`）→ Google 相册（`com.google.android.apps.photos`）的同步事务 **46 分钟未返回**（`elapsed 2802649ms`）
- system_server 的 binder 线程被 GMS / 地图 / Gmail / Chrome / Nekogram 的 pending 同步事务占住（47–49 分钟），同一进程列表全部可对照 `ps -A -o pid=,args=` 解析
- 时间线与 NoActive 深度睡眠（`dozeType: locked`，锁屏 60 秒后挂起全部非白名单用户应用）完全吻合；深度睡眠退出后进程已恢复（`ps` 状态 `S`），但 pending 事务**永不消费**——binder 唤醒通知丢失

**根因**：Google 相册没进 NoActive 白名单。深度睡眠挂起相册后，挂起进程不再消费 binder 事务——media.module 对相册的调用永不返回，其 binder 线程池被占死，选择器查询永远排队；system_server 线程池同样被占 → 壁纸等系统 binder 调用卡死。「偶尔正常」= 挂起进程恰好被解冻、堆积事务侥幸被消费的间隙。

**解决**：Google 相册加入 NoActive 白名单（连同 GMS 等实际在用的 Google 应用）。

**教训**：**正确的冻结名单比 Re:Kernel 钩子更重要**——钩子解决「冻结发生时 binder 事务怎么正确处理」，名单决定「该不该冻结」。相册是照片选择器链路依赖的服务提供者，被冻结后整个进程不在运行，无论钩子多好都救不回来。
