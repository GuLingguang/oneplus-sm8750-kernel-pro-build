# OnePlus Ace 6 Kernel Builder

> [English](README.md) | **中文（简体）**

> OnePlus Ace 6 (ktm, SM8750) 自定义内核构建器 —— 可配置的 GitHub Actions 构建，支持 ReSukiSU + SUSFS + Droidspaces + Re:Kernel，已在 Project Infinity X（Android 16）上验证。

![GitHub Release](https://img.shields.io/github/v/release/GuLingguang/oneplus-sm8750-kernel-pro-build)
![GitHub License](https://img.shields.io/github/license/GuLingguang/oneplus-sm8750-kernel-pro-build)
![Build](https://img.shields.io/github/actions/workflow/status/GuLingguang/oneplus-sm8750-kernel-pro-build/build.yml?label=build&logo=githubactions)
![Drift check](https://img.shields.io/github/actions/workflow/status/GuLingguang/oneplus-sm8750-kernel-pro-build/upstream-check.yml?label=drift%20check)
![Clean ccache](https://img.shields.io/github/actions/workflow/status/GuLingguang/oneplus-sm8750-kernel-pro-build/clean-ccache.yml?label=clean-ccache)

---

## 目录

- [概览](#概览)
- [仓库一览](#仓库一览)
- [刷机免责声明](#刷机免责声明)
- [平台兼容性](#平台兼容性)
- [验证证据](#验证证据)
- [真机截图](#真机截图)
- [功能开关](#功能开关)
- [功能详情](#功能详情)
- [使用方法](#使用方法)
- [产物与 Release](#产物与-release)
- [适配说明](#适配说明)
- [可复现性](#可复现性)
- [本地构建](#本地构建)
- [仓库结构](#仓库结构)
- [自定义与优化（Customizations）](docs/CUSTOMIZATIONS_zh.md)
- [路线图与寻求帮助](#路线图与寻求帮助)
- [致谢](#致谢)
- [许可证](#许可证)

---

## 概览

为 **SM8750（骁龙 8 Elite）平台**构建自定义内核 —— 面向 **OnePlus Ace 6**（代号 `ktm`），运行 **Project Infinity X**（基于 LineageOS，Android 16，内核 6.6.142）。

> **命名说明**：海外版「OnePlus 15R」对应 **Ace 6T**，属于另一款设备。本项目仅适用于 Ace 6（`ktm`），不适用于 15R 或 Ace 6T。

> **测试范围**：目前只在 Project Infinity X 上完成测试。ColorOS/OxygenOS 以及尚未进行设备验证的 ROM 均不提供兼容性结论，详见[免责声明](#刷机免责声明)。

> **仓库范围**：CI 每次构建都会从上游 `lineage-23.2` 获取内核源码。本仓库存放经过审查的增量内容：补丁、额外内核源码、profile、workflow 和构建规则。AK3 zip 在通过发布门槛前仅作为本地或 CI 候选产物。

各功能在 GitHub Actions 中均有独立输入；只有存在明确的源码或运行时冲突时，profile 校验才会拒绝组合。

内核基于**官方 Ace6 内核源码**（lineage-23.2 分支），配合**官方预编译 vendor 模块**（来自 ROM 的 vendor_dlkm）。当前构建路径具有以下特征：

- 无需重建整个模块树（UFS/GPU 等来自 ROM）
- 设备接受当前构建路径生成的**基于 commit 的版本串**。早期 vermagic workaround 已不属于当前构建（详见[验证证据](#验证证据)）。

## 仓库一览

| | 内容 |
|---|---|
| **9 个功能补丁** | 针对 lineage-23.2 树的独立适配 |
| **额外内核源码** | SUSFS、EVDI、LZ4/LZ4KD/zstd、NTSYNC 和 Baseband Guard 源码 |
| **API 适配** | SUSFS 与 Re:Kernel 集成均锁定在已审查的 6.6.142 源码接口 |
| **CI 设计** | 共用 profile/build 入口、锁定工具链和构建 manifest；仓库检查与 WebUI 检查分开执行 |
| **真机验证** | 一台 Ace 6 上 ReSukiSU + SUSFS Inline 已完成启动/root/基础 smoke/5 分钟初筛；完整功能验收仍未完成 |
| **维护** | 无需维护 fork 树 —— 锁定增量按需应用到上游 `lineage-23.2` |

---

## 刷机免责声明

> [!WARNING]
> 本内核仅在**一台设备、一个 ROM**上测试过。刷入前请阅读以下说明。

### 兼容性

| ROM | 状态 |
|---|---|
| **Project Infinity X**（v3.12，Android 16） | 已测试可用（OnePlus Ace 6 `ktm`） |
| **LineageOS**（Ace6 构建） | 未测试，不提供兼容性结论 |
| **ColorOS / OxygenOS** | 不支持，vendor 集成方式不同 |
| 其他 | — 未评估 |

### 刷机前

1. **备份 boot 分区** —— 刷入前必须保留可恢复的官方镜像
2. **本内核仅处理 `boot` 分区** —— 不要写入其他分区；设备分区布局存在差异，错误操作可能导致无法启动
3. **设备必须运行 LineageOS 系 ROM**（如 Infinity X）—— 原版 ColorOS/OxygenOS 上无法使用
4. 这是**社区项目**，不提供商业质保或付费技术支持

### 出现 bootloop 时

- 按照设备的恢复流程操作
- 恢复已备份的官方 boot 镜像
- 官方 `boot.img` 也可以从原版 ROM zip（`payload.bin`）里提取

> [!CAUTION]
> **只在 Project Infinity X 上测试过。** LineageOS、ColorOS 和 OxygenOS 均没有对应的真机验证结论。无法确认环境时，请先备份并自行评估刷入风险。

## 平台兼容性

### SM8750 平台

本项目面向 **SM8750（骁龙 8 Elite）平台**。内核、模块和设备树源码来自平台的 lineage-23.2 原版树。简版 ROM 兼容表见[免责声明](#刷机免责声明)，详细范围如下：

- `lineage-23.2` SM8750 树家族**跨设备共享** —— 同一套内核/模块/设备树支撑 Ace6、其他 OnePlus SM8750 设备和它们的 LOS 系 ROM。每台设备不同的是 **vendor 集成**（设备专属模块和固件），所以在一台设备上能开机的内核，另一台可能拒绝启动。
- **其他 OnePlus SM8750 设备**：未验证，不提供兼容性结论。不同设备的 vendor 集成、固件和分区布局可能导致无法启动。

## 验证证据

实测于 **OnePlus Ace 6（`ktm`），Project Infinity X / Android 16**（2026-09-06；主 profile 后续验证于 2026-09-07）。下表仅包含已记录的证据：

| 项目 | 证据 |
|---|---|
| **内核版本** | `6.6.142-4k-g<12位commit>` —— LOCALVERSION 使用真实上游 commit |
| **启动/root/基础运行** | ReSukiSU + SUSFS Inline 在 Ace 6 `PLQ110` 启动；root ADB、Wi‑Fi/LTE/显示/触控/传感器 smoke 和 5 分钟只读初筛通过 |
| **ReSukiSU** | v4.1.0（构建号 **35046**）—— 可连接 KernelSU 管理器 |
| **zram 与回写** | 主 profile 使用 `lz4kd`，启用全部 9 种压缩算法；`/dev/block/sda13` 作为 1 GiB 回写设备，zram 大小为 6 GiB，swap 已启用；手动触发回写返回成功 |
| **zram 模块职责** | `Scene` 管理大小、算法和 swap；`ZramWritebackBoost` 管理调度；`azram-backing` 只负责 backing hand-off，未发现职责冲突 |
| **vendor 只读** | `/vendor`、`/vendor_dlkm`、`/odm`、`/system_dlkm` 全部 EROFS；写入尝试被拒绝 |

尚未完成的验证：

- **Re:Kernel** 内核侧已可构建，但 NoActive userspace 协议和运行时门槛仍未验证；不作发布声明
- **KPM/KPN** 仅保留工具链钩子；当前发布 profile 未启用，未在真机验证
- **Droidspaces / EVDI** 已完成内核侧构建和驱动加载验证；容器生命周期、显示链路和 userspace ABI 尚未完成验收
- **LineageOS**（官方 Ace6 构建）未确认；测试机运行的是 Project Infinity X

## 真机截图

拍摄于同一台测试机（OnePlus Ace 6 `ktm`，Project Infinity X v3.12）。点击任意缩略图查看原图。

<table>
  <tr>
    <td align="center"><a href="docs/screenshots/ksu_manager.png"><img src="docs/screenshots/ksu_manager.png" width="150" alt="ReSukiSU"></a></td>
    <td align="center"><a href="docs/screenshots/susfs.png"><img src="docs/screenshots/susfs.png" width="150" alt="SuSFS"></a></td>
    <td align="center"><a href="docs/screenshots/zram_all_algos.png"><img src="docs/screenshots/zram_all_algos.png" width="150" alt="全压缩算法"></a></td>
    <td align="center"><a href="docs/screenshots/zram_writeback.png"><img src="docs/screenshots/zram_writeback.png" width="150" alt="lz4kd + writeback"></a></td>
    <td align="center"><a href="docs/screenshots/droidspaces.png"><img src="docs/screenshots/droidspaces.png" width="150" alt="Droidspaces"></a></td>
  </tr>
  <tr>
    <td align="center"><b>① ReSukiSU</b></td>
    <td align="center"><b>② SuSFS</b></td>
    <td align="center"><b>③ 全压缩算法</b></td>
    <td align="center"><b>④ LZ4KD + writeback</b></td>
    <td align="center"><b>⑤ Droidspaces</b></td>
  </tr>
  <tr>
    <td align="center"><a href="docs/screenshots/bbg_erofs.png"><img src="docs/screenshots/bbg_erofs.png" width="150" alt="Baseband Guard"></a></td>
    <td align="center"><a href="docs/screenshots/network.png"><img src="docs/screenshots/network.png" width="150" alt="Better network"></a></td>
    <td align="center"><a href="docs/screenshots/banner.png"><img src="docs/screenshots/banner.png" width="150" alt="构建标签"></a></td>
    <td align="center"><a href="docs/screenshots/rekernel.png"><img src="docs/screenshots/rekernel.png" width="150" alt="Re:Kernel"></a></td>
    <td align="center"><a href="docs/screenshots/bbr.png"><img src="docs/screenshots/bbr.png" width="150" alt="BBR"></a></td>
  </tr>
  <tr>
    <td align="center"><b>⑥ Baseband Guard</b></td>
    <td align="center"><b>⑦ Better network</b></td>
    <td align="center"><b>⑧ 构建标签</b></td>
    <td align="center"><b>⑨ Re:Kernel</b></td>
    <td align="center"><b>⑩ BBR</b></td>
  </tr>
</table>

当前未完成：**KPM/KPN**（尚未真机测试）。

---

## 功能开关

| 开关 | 默认 | 说明 |
|---|---|---|
| **KernelSU** | `none` | ReSukiSU（内建 KSU）或无 |
| **SUSFS** | 关 | 增强的挂载/root 隐藏（需要 KSU） |
| **lz4 1.10 + zstd 1.5.7** | 关 | 压缩性能（新算法，ARM64 NEON） |
| **LZ4KD** | 关 | 额外的 lz4 变体，用于 zram |
| **All zram algorithms** | 关 | 启用 `comp_algorithm` 中全部 zram 压缩器（含 lz4hc/842；容器/Droidspaces 场景有用） |
| **ZRAM writeback** | 关 | 将空闲/不可压缩的 zram 页写入后备设备（运行时需配置 `backing_dev`） |
| **Droidspaces** | 关 | 轻量 Linux 容器支持（standard/extend） |
| **Baseband Guard** | 关 | 内核级防格式化保护 |
| **CVE patches** | 关 | GhostLock（CVE-2026-43499 + CVE-2026-53163）—— 上游现已包含，补丁已移除 |
| **Better network** | 关 | ipset/iptables 高级网络支持 |
| **BBR** | 关 | TCP 拥塞控制 |
| **KPM/KPN** | 关 | KernelPatch Next（独立内核补丁支持） |
| **Re:Kernel** | 关 | Freezer/NoActive binder 通知钩子 |
| **Kernel suffix** | 空 | 自定义版本后缀（如 `perf` → `6.6.142-4k-perf`） |
| **Attribution** | 开 | 构建标签（user/host/REPO_NAME/AK3） |
| **Artifacts** | ak3 | `ak3` 候选 zip；裸 `Image` 仅本地，`boot.img`/`all` 被阻止 |
| 🕐 **Build time** | 空 | 自定义构建时间戳（`KBUILD_BUILD_TIMESTAMP`）。CI 上所有构建时间戳通过 faketime 固定为 `2025-05-25` 以保证可复现 —— 自定义值会覆盖内核内嵌时间。本地（reproduce.sh）留空 = 当前 UTC |
| 💾 **Public ccache** | 关 | 上传构建缓存到 Release，加速重复构建 |
| 🔍 **ccache debug** | 关 | 上传 ccache 日志 |

---

## 功能详情

### KernelSU (ReSukiSU)

- 克隆 [ReSukiSU](https://github.com/ReSukiSU/ReSukiSU)（完整历史 —— 版本号 = `30000 + 提交数 + 700`）
- 应用 7 个强制手动钩子（execveat/stat/faccessat/sys_read/sys_reboot/input/setresuid）
- 已验证版本 35046（`v4.1.0`）

### SUSFS

- 来自 [simonpunk/susfs4ksu](https://gitlab.com/simonpunk/susfs4ksu)（`gki-android15-6.6` 分支）
- 25 个主树文件 + 16 个 KernelSU 内部适配文件
- 包含以下 susfs 功能：sus_path、sus_mount、sus_kstat、uname 伪装、cmdline 伪装、open_redirect、sus_map、AVC 日志伪装

### Droidspaces

- `standard`：容器 + ntsync（NT 同步原语）
- `extend`：+ EVDI 虚拟显示、虚拟 HCI、systemd-coredump
- 内核配置：PID_NS/USER_NS/SYSVIPC/DEVTMPFS/POSIX_MQUEUE/namespaces

### Re:Kernel

- **源码级集成**：netlink 服务器 + binder 钩子（reply/transaction/free_buffer_full）+ signal 钩子 —— LKM 方案试过之后放弃了（这棵树的符号不满足它需要的钩子）
- 代码位于 `#ifdef CONFIG_REKERNEL` 条件内；关闭该选项时不参与编译
- 针对 `lineage-23.2` 树（6.6.142）适配：`proc_ops` API、不同的 `binder_alloc`/`signal.c` 签名

> **已知限制 —— NoActive 白名单**：当 **Google 相册未加入 NoActive 白名单**时，照片选择器（**相册与视频 Photos and videos** 权限 → **允许受限访问 Allow limited access** 模式）会停留在空白加载页面，壁纸无法更换。深度睡眠或冻结相册后，media.module 对相册的调用不会返回，其 binder 线程池停止处理请求，选择器查询持续排队；`system_server` 的 binder 线程也可能被其他冻结的 Google 应用（GMS/地图/Gmail/Chrome）的同步事务占用。诊断：`adb shell su -c "cat /dev/binderfs/binder_logs/transactions"`，查找 `elapsed` 较大的 pending 事务，再用 `ps -A -o pid=,args=` 解析进程。测试前应将 **Google 相册**及实际需要的 Google 应用加入 NoActive 白名单。

### Baseband Guard

- 来自 [cctv18/Baseband-guard](https://github.com/cctv18/Baseband-guard)
- 基于 LSM 的防格式化保护（阻止写入非用户分区）

### GhostLock（CVE-2026-43499 + CVE-2026-53163）

两个漏洞现在都已由上游 `lineage-23.2` 覆盖：
- **CVE-2026-43499**：rtmutex `remove_waiter` NULL 防护 —— 锁定的上游 6.6.142 树自带（`scoped_guard`）
- **CVE-2026-53163**：`rtmutex_api.c` 中 proxy cleanup 的 `ret < 0` 修复 —— 上游已合入 `UPSTREAM: locking/rtmutex: Skip remove_waiter() when waiter is not enqueued`（2026-08-18 推送到 `lineage-23.2`）

独立的 `08_cve.patch` 因此已移除。

### 压缩

- lz4 1.10（新库结构，ARM64 NEON 快速解压）
- zstd 1.5.7
- LZ4KD（来自 [ShirkNeko/SukiSU_patch](https://github.com/ShirkNeko/SukiSU_patch)）—— 用于 zram 的独立算法

---

## 使用方法

### 首次 Fork（一次性准备）

1. **Fork** 本仓库
2. **允许写入权限**：Settings → Actions → General → Workflow permissions → **Read and write**（Release 上传必需）
3. 先运行一次 **Upload AOSP Clang Toolchain** workflow。该 workflow 将官方工具链（clang 21.0.0 r563880c，约 1.5 GB）打包并上传到 fork 仓库的 Release，构建从该 Release 下载（没有 apt 备用源）
4. 向默认分支提交任意 commit，激活每周仅报告的上游漂移检查

### 构建

1. 进入 **Actions** → **Build Ace6 Kernel** → **Run workflow**
2. 选择所需功能，点击 **Run workflow**
3. 从 run 的 **artifacts** 下载 AK3 zip（`release_enable` 开启时也可从 Release 下载）
4. 构建时间取决于 runner、并行度和 ccache 命中率；首次构建通常明显慢于后续构建

### 刷入

1. **先备份当前槽位的 boot 分区** —— 用 OrangeFox（OFRP）或任意 recovery 的内置备份，或：
   `adb shell "dd if=/dev/block/by-name/boot_$(getprop ro.boot.slot) of=/sdcard/boot_backup.img"`
2. 通过 recovery（TWRP / OrangeFox / AOSP recovery）刷入 AK3 zip（`Kernel-Ace6-*.zip`）：Install → 选择 zip → 重启；或通过 KernelSU 管理器安装（Install → 刷镜像）。AnyKernel3 会自动刷**当前活动槽位**的 `boot` 分区（`boot_a` / `boot_b`，取决于当前运行槽）
3. **分区要求**：本内核仅写入 `boot`，不写入 `init_boot` 或非活动槽位
4. 出现 bootloop 时，恢复备份的官方 boot 镜像

### 工具链

- 使用 **AOSP Clang 21.0.0 (r563880c)** —— 与官方 OnePlus 内核构建完全相同的工具链
- 构建从**fork 仓库的 `toolchain-AOSP-Clang-21.0.0-r563880c` Release**下载；首次 fork 后必须先运行上传 workflow，流水线没有 apt.llvm.org 备用源

### 备注

- 默认 workflow 是**最小构建**（无 KSU、无功能）；需要其他功能时单独选择对应开关
- `kernel_suffix` 和 `build_time` 用于标识构建并固定相应输入
- Attribution 默认 `Lingguang@kernel-builder` —— 可通过 `build_user`/`build_host` 修改，或用 `attribution_enable` 完全关闭

---

## 产物与 Release

本仓库将内核刷机包、裸开发产物和独立 KSU 模块分别管理：

| 产物 | 位置 | 可刷？ | 说明 |
|---|---|---|---|
| **AK3 zip**（`Kernel-Ace6-<用户>-ksu<版本>-<日期>.zip`） | `artifact_mode = ak3` | 可作为刷机候选 | AnyKernel3 包；独立 KSU 模块不会嵌入其中 |
| **`Image`** | 仅本地 `artifact_mode = image` | 不可刷入 | 裸开发产物，没有目标 ramdisk/DTB/AVB 封装 |
| **`boot.img` / `all`** | 当前不产出 | 阻止 | 需要目标 boot 输入；构建器拒绝用猜测参数伪造 |
| **独立 KSU 模块 zip** | `independent_modules = true` | 在 KernelSU 中单独安装 | 每个自有模块一个 zip；不会静默塞进 AK3 |
| **`toolchain-…` / `ccache-…` Release** | Releases 页 | 不可刷入 | 构建基础设施（工具链 / ccache），不是内核 |

- Run 产物保留 **14 天**（`build.yml` 里的 `retention-days`）；Release 长期保留
- Release 标签形如 `kernel-20260803-115320-ksu35046` —— 该次构建参数的时间点快照
- Release 发布仍是独立门槛；`release_enable` 只记录请求意图，workflow 还要求运行时、回滚和交接证据使 `release_allowed=true`。本地构建不会发布。

---

## 适配说明

本项目把多个来源的补丁（主要是 [cctv18/oppo_oplus_realme_sm8750](https://github.com/cctv18/oppo_oplus_realme_sm8750) 项目，针对一加官方 OKI 树）适配到 **Ace6 内核树**（`lineage-23.2`，内核 6.6.142）。关键适配：

- **补丁**拆分为独立开关（`patches/split/00-07, 09`）：`07_compile_fixes.patch` 无条件应用，其余由 workflow 功能开关控制（KSU/SUSFS/lz4/LZ4KD/Droidspaces/BBG/Re:Kernel）
- **新文件**（补丁无法创建的部分）放在 `patches/extra/` —— lz4/zstd 库、susfs.c、evdi、ntsync、Baseband-guard
- **Re:Kernel** 使用适配到 lineage-6.6.142 API 的源码钩子（netlink + binder/signal）
- **模块**来自 ROM 官方预编译 `vendor_dlkm` —— 无需重建模块树
- 部分一加官方独占功能（Fengchi scx 调度器、ADIOS IO 调度器）**未移植** —— 源码只存在于官方 OKI 树中

## 可复现性

- **LOCALVERSION 用真实 commit**（来自 GitHub API，因为源码是 zip 没有 .git）
- **`KBUILD_BUILD_TIMESTAMP`** 用于自定义/固定构建时间
- **ccache** 配 sloppiness（忽略文件 mtime/ctime）加速重复构建
- **Public ccache**（可选 `ccache_update`）：打包并上传缓存到 Release，近乎即时重建
- **上游漂移体检**：`check_upstream.sh`（以及每周 workflow）把锁定步骤按顺序应用到最新 `lineage-23.2` 快照，上传 JSON/Markdown 报告和 Issue 草稿；不会自动创建或修改 Issue
- 已在本地验证：共生成 5 个带 manifest 的 AK3 候选，其中一个 ReSukiSU + SUSFS Inline 候选通过部分真机验收；未宣称 CI 等价或完整功能验收

**GitHub 免费额度**：Actions 每月提供 2,000 分钟和 1 GB 缓存；本仓库的 ccache Release asset 约 630 MB，toolchain asset 约 1.5 GB。重复构建会消耗这些额度。频繁的本地构建可使用 `reproduce.sh`，CI 适合需要托管 runner 的场景。

---

## 本地构建

仓库自带**跨机器本地构建脚本** —— `reproduce.sh`：

```bash
./reproduce.sh                          # 最小构建（无功能）
./reproduce.sh --ksu resukisu --susfs   # 带 ReSukiSU + SUSFS
./reproduce.sh --bbg --lz4 --lz4kd      # 已锁定的可选功能
./reproduce.sh --dry-run                # 不下载、不修改源码，只校验 ID/锁
python3 scripts/ci.py                   # 运行仓库级 CI 闸门
```

`reproduce.sh` 只是 `scripts/build.py` 的本地适配器，Actions 也调用同一个
入口。共同入口解析精确的 profile/源码锁，把 `KERNEL_SRC` 克隆到隔离工作区
而不修改它，按顺序应用补丁、运行 `olddefconfig`、用 Image 实际版本串校验
`kernel.release`，并在 AK3 旁生成 build manifest。Re:Kernel 和主 extend 组合
允许本地构建但会保留运行时警告；KPM 仍在资源锁定前明确拒绝。详见
`./reproduce.sh --help` 和
`docs/execution-t15.md`。

**依赖**：锁定的 AOSP Clang 21 工具链、git、patch、zip、make、bc、flex、
bison、Python 3 和 `strings`。Actions 会安装宿主包，并在共同入口前校验工具链
压缩包 hash。

**目录卫生**：所有中间产物（源码、打补丁后的树、AK3 打包目录）都在
`work/`；可丢弃的日志/报告放在 `work/_tmp/`；产物和 `build-manifest.json` 写入 `out/`。
`./reproduce.sh --clean`
只清理选定的 work 目录重新构建；不会修改外部源码提供目录。

---

## 仓库结构

```
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md         # Bug 模板：ROM、开关、日志
│   │   └── bug_report_zh.md      # 中文 Bug 模板
│   └── workflows/
│       ├── ci.yml                 # Push/PR：仓库和 WebUI 检查
│       ├── build.yml             # 主构建 workflow（手动触发，24 个输入）
│       ├── clean-ccache.yml      # 手动：清理 GitHub 缓存 / Release ccache asset
│       ├── upstream-check.yml    # 每周：补丁在上游还能打上吗？
│       └── upload-toolchain.yml  # 一次性：上传 AOSP clang 到 Release
├── patches/
│   ├── split/                    # 9 个独立功能补丁（00-07, 09）
│   ├── extra/                    # 补丁无法创建的新文件
│   │   ├── fs/  crypto/  drivers/  include/  lib/
│   │   │                         # susfs.c, evdi, ntsync, lz4/lz4kd/zstd, headers
│   │   └── Baseband-guard/       # 防格式化 LSM
│   └── 02_ksu.patch              # SUSFS KernelSU 内部适配
├── config/
│   └── config_ace6_final.config  # 基础内核配置（来自设备）
├── docs/
│   ├── CUSTOMIZATIONS.md         # 设备端自有修改（英文）
│   ├── CUSTOMIZATIONS_zh.md      # 设备端自有修改（中文）
│   └── screenshots/              # 10 张真机证明
├── modules/
│   ├── azram-backing/            # KSU 模块：开机配置 hybridswap backing（最先执行）
│   ├── selinux_perf/             # KSU 模块：窄范围 perf-HAL SELinux 权限例外
│   └── tcp-config/               # KSU 模块：TCP 算法/qdisc WebUI
│       └── webui-src/            # WebUI 构建源码（npm + esbuild）
├── ak3/                          # AnyKernel3 模板（tools/, META-INF/）
├── lib/                          # faketime 库 + ccache-ECS
├── LICENSE
├── check_upstream.sh             # 仅报告的累积漂移检查包装器
├── scripts/ci.py                 # 无网络仓库 CI 闸门
├── scripts/drift.py              # 快照检查器及报告/Issue 草稿生成器
└── reproduce.sh                  # 本地构建脚本
```

---

## 路线图与寻求帮助

构建路径已实现，一份 profile 已有部分真机证据；发布和功能门槛仍未关闭。下表列出当前可协助的事项：

**测试需求** —— 优先需要官方 LineageOS（Ace6）用户提供确认报告。

| 项目 | 状态 | 协助方式 |
|---|---|---|
| **Re:Kernel 运行时验证** | ⛔ 受 NoActive userspace/运行时门槛阻塞 | 提供匹配的 userspace 和真机证据 |
| **KPM/KPN 真机测试** | ⏳ 工具链就绪，未实践 | 加载一个 KPM 模块，回报哪些正常/异常 |
| **LineageOS (Ace6) 确认** | 未验证 | 在官方 LineageOS 上刷，用 [中文 bug 模板](.github/ISSUE_TEMPLATE/bug_report_zh.md) 提交 issue |
| **其他 SM8750 设备** | 同树家族，未验证 | 提供设备证据前先备份 `boot` |

**维护说明**：作者跟进上游 `lineage-23.2` 和 ReSukiSU 的变化。树发生变化并导致补丁无法应用时，`reproduce.sh` 会在补丁阶段报告错误；请提交 issue 记录影响范围。

**参与**：详见 [CONTRIBUTING_zh.md](CONTRIBUTING_zh.md) 了解什么样的报告或 PR 更有用。

**版本**：Release 标签遵循 `kernel-<时间戳>-<功能标记>`——是那次构建的瞬时快照。目前没有升级路径承诺；标签或本地 AK3 zip 只是候选记录，不代表已授权发布。

**计划中的功能**（都需要从官方 OKI 树移植 —— lineage 树里没有源码）：

- **Fengchi（风驰）scx 调度器** —— 一加官方的 sched_ext 调度器
- **ADIOS IO 调度器** —— 一加官方的定制块层调度器
- **官方 Ace6 120W SUPERVOOC 快充** —— 内核侧 vooc 协议栈；LOS ROM 的 vendor 侧可能不配合，真机充电效果是验证目标

以上项目尚未作实施承诺；开始移植后再更新状态。

---

## 致谢

本项目使用了下列项目和开发者提供的代码、补丁或基础设施。

### 主要灵感与补丁来源

| 项目 | 用途 |
|---|---|
| [cctv18/oppo_oplus_realme_sm8750](https://github.com/cctv18/oppo_oplus_realme_sm8750) | **主要参考** —— workflow 设计、补丁结构、lz4/zstd/Droidspaces/BBG 集成、ccache-ECS、faketime |
| [Ace6-Development/android_kernel_oneplus_sm8750](https://github.com/Ace6-Development/android_kernel_oneplus_sm8750) | 内核源码（lineage-23.2） |
| [Ace6-Development/android_kernel_oneplus_sm8750-modules](https://github.com/Ace6-Development/android_kernel_oneplus_sm8750-modules) | 模块源码（符号链接目标） |
| [LineageOS/android_kernel_oneplus_sm8750-devicetrees](https://github.com/LineageOS/android_kernel_oneplus_sm8750-devicetrees) | 设备树源码 |

### 功能来源

| 项目 | 用途 |
|---|---|
| [ReSukiSU/ReSukiSU](https://github.com/ReSukiSU/ReSukiSU) | KernelSU 实现 |
| [simonpunk/susfs4ksu](https://gitlab.com/simonpunk/susfs4ksu) | SUSFS 内核补丁 |
| [ShirkNeko/susfs4ksu](https://github.com/ShirkNeko/susfs4ksu) | SUSFS 镜像 |
| [Sakion-Team/Re-Kernel](https://github.com/Sakion-Team/Re-Kernel) | Re:Kernel 源码钩子 |
| [KernelSU-Next/KPatch-Next](https://github.com/KernelSU-Next/KPatch-Next) | KPM/KPN 工具链 |
| [ShirkNeko/SukiSU_patch](https://github.com/ShirkNeko/SukiSU_patch) | LZ4KD 算法 |
| [cctv18/Baseband-guard](https://github.com/cctv18/Baseband-guard) | 防格式化 LSM |
| [ravindu644/Droidspaces-OSS](https://github.com/ravindu644/Droidspaces-OSS) | Droidspaces 容器 |
| [zzh20188/GKI_KernelSU_SUSFS](https://github.com/zzh20188/GKI_KernelSU_SUSFS) | GhostLock CVE 链、构建时间、参考 |

### 工具与基础设施

| 项目 | 用途 |
|---|---|
| [Android AOSP clang prebuilts](https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86) | 官方工具链（r563880c） |
| [osm0sis/AnyKernel3](https://github.com/osm0sis/AnyKernel3) | AK3 刷机 zip 模板 |
| [cctv18/ccache-ECS](https://github.com/cctv18/ccache-ECS) | 专业内核构建缓存 |
| [ferstar/lz4-zstd](https://github.com/ferstar) | lz4/zstd 算法更新（经 cctv18） |
| [Xiaomichael](https://github.com/Xiaomichael) | lz4/zstd 移植（经 cctv18） |

### 致谢

- [**@cctv18**](https://github.com/cctv18) —— 整套构建流水线概念、补丁集成、ccache 优化思路
- [**@NullCode1337**](https://github.com/NullCode1337) —— Project Infinity X ROM 与 Ace6 内核开发
- **所有让自定义内核成为可能的上游内核/Android 项目**

---

## 许可证

[GPL-2.0](LICENSE)
