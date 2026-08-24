# OnePlus Ace 6 Kernel Builder

> [English](README.md) | **中文（简体）**

> OnePlus Ace 6 (ktm, SM8750) 自定义内核构建器 —— 可配置的 GitHub Actions 构建，支持 ReSukiSU + SUSFS + Droidspaces + Re:Kernel，已在 Project Infinity X（Android 16）上验证。

![GitHub Release](https://img.shields.io/github/v/release/GuLingguang/oneplus-sm8750-kernel-pro-build)
![GitHub License](https://img.shields.io/github/license/GuLingguang/oneplus-sm8750-kernel-pro-build)
![Build](https://img.shields.io/github/actions/workflow/status/GuLingguang/oneplus-sm8750-kernel-pro-build/build.yml?label=build&logo=githubactions)
![Drift check](https://img.shields.io/github/actions/workflow/status/GuLingguang/oneplus-sm8750-kernel-pro-build/upstream-check.yml?label=drift%20check)
![Clean ccache](https://img.shields.io/github/actions/workflow/status/GuLingguang/oneplus-sm8750-kernel-pro-build/clean-ccache.yml?label=clean-ccache)

---

## 📖 目录

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

为 **SM8750（骁龙 8 Elite）平台**构建自定义内核 —— 面向 **OnePlus Ace 6**（代号 `ktm`），运行 **Project Infinity X**（基于 LineageOS，Android 16，内核 6.6.139）。

> ℹ️ **命名说明**：海外版「OnePlus 15R」对应的是 **Ace 6T** —— 是*另一款*设备。本内核只适配 Ace 6（`ktm`），不要在 15R / Ace 6T 上刷。

> ⚠️ **只在 Project Infinity X 上测试过** —— 不适用于 ColorOS/OxygenOS。LineageOS（Ace6）上大概率可用，详见[免责声明](#刷机免责声明)。

> 💡 **这个仓库是什么**：在找内核源码？CI 每次构建都会从上游 `lineage-23.2` 现拉。本仓库存放的是**增量**——补丁、额外 C 源码、workflow——刷机产物发布在 [Releases](https://github.com/GuLingguang/oneplus-sm8750-kernel-pro-build/releases)。

每个功能都是 GitHub Actions 里的**可选开关**——只构建你需要的，多一样都不要。

内核基于**官方 Ace6 内核源码**（lineage-23.2 分支），配合**官方预编译 vendor 模块**（来自 ROM 的 vendor_dlkm），这意味着：

- 无需重建整个模块树（UFS/GPU 等来自 ROM）
- 设备接受**基于真实 commit 的版本串**——我们一开始伪装过 vermagic，后来不伪装了，设备根本不在乎（详见[验证证据](#验证证据)）

## 仓库一览

| | 内容 |
|---|---|
| **9 个功能补丁** | **29,148 行**针对 lineage-23.2 树的适配 |
| **额外 C 源码** | **20,775 行** —— susfs.c、EVDI 驱动、lz4/lz4kd/zstd 库、ntsync、Baseband-guard |
| **API 适配** | **共 16 处** —— 11 处 SUSFS（新版 KSU API）+ 5 处 Re:Kernel（lineage 6.6.139 签名差异） |
| **CI 设计** | 32 步、24 个输入、指纹 ccache —— 全量构建约 8 分钟 |
| **真机验证** | **567 个官方 ROM 模块**全部正常加载运行；vendor 分区 EROFS 只读 |
| **维护** | 无需维护 fork 树 —— 增量就是 9 个补丁 + 额外源码，按需应用到上游 `lineage-23.2` |

---

## ⚠️ 刷机免责声明

> [!WARNING]
> 这颗内核只在**一台设备、一个 ROM**上测试过 —— 刷机前请先阅读。

### 兼容性

| ROM | 状态 |
|---|---|
| **Project Infinity X**（v3.12，Android 16） | ✅ 已测试可用（OnePlus Ace 6 `ktm`） |
| **LineageOS**（Ace6 构建） | 🤔 大概率可用 —— 内核/模块/设备树都是原版 LineageOS，只加了非破坏性的 Ace6 适配（MPC7022 电量计、TMS NFC），但**未在真机确认** |
| **ColorOS / OxygenOS** | ❌ **不支持** —— 大概率无法开机（vendor 集成方式不同） |
| 其他 | 🏴☠️ 未知领域 |

### 刷机前

1. **备份 boot 分区** —— 你以后会感谢自己
2. **这颗内核只碰 `boot` 分区** —— 不要刷任何其他东西（设备已熔断；动其他分区可能变砖）
3. **设备必须运行 LineageOS 系 ROM**（如 Infinity X）—— 原版 ColorOS/OxygenOS 上无法使用
4. 这是**社区项目** —— 没有保修、没有客服热线、没有退款

### 如果 bootloop 了

- 保持冷静（或者不冷静也行，我们不会评判）
- 恢复你的官方 boot 镜像（这就是你备份的原因！）
- 官方 `boot.img` 也可以从原版 ROM zip（`payload.bin`）里提取

> [!CAUTION]
> **只在 Project Infinity X 上测试过。** LineageOS *大概*没问题，ColorOS/OxygenOS *大概*不行。拿不准就备份后自行承担风险刷入。

## 平台兼容性

### SM8750 平台

本项目面向 **SM8750（骁龙 8 Elite）平台** —— 内核、模块、设备树源码全部是平台的 lineage-23.2 原版树。简版 ROM 兼容表在[免责声明](#刷机免责声明)里；详细版就一段话：

- `lineage-23.2` SM8750 树家族**跨设备共享** —— 同一套内核/模块/设备树支撑 Ace6、其他 OnePlus SM8750 设备和它们的 LOS 系 ROM。每台设备不同的是 **vendor 集成**（设备专属模块和固件），所以在一台设备上能开机的内核，另一台可能拒绝启动。
- **其他 OnePlus SM8750 设备**（如果用这套树家族）：🧪 大概率可用，**完全未验证** —— 自行测试风险自负，先备份。

## 验证证据

实测于 **OnePlus Ace 6（`ktm`），Project Infinity X v3.12**（2026-08-03）。下表每一行都是在设备上观察到的：

| 项目 | 证据 |
|---|---|
| **内核版本** | `6.6.139-4k-g<12位commit>` —— LOCALVERSION 用真实上游 commit |
| **官方 ROM 模块** | 全部 **567** 个 vendor 模块（`vendor_dlkm`）在自定义内核下正常加载运行。ROM 模块的版本串不同（`-gdc4c44f3ecc0-dirty`）——从未造成问题，MODVERSIONS 符号校验才是设备真正执行的检查 |
| **ReSukiSU** | v4.1.0（构建号 **35046**）—— 可连接 KernelSU 管理器 |
| **zram 压缩器** | `comp_algorithm` 中可见 `lz4kd`（zram 已内建——ROM 预编译的 `zram.ko` 才是遮住列表的元凶）；开 `show_all_algos` 显示完整算法列表 |
| **vendor 只读** | `/vendor`、`/vendor_dlkm`、`/odm`、`/system_dlkm` 全部 EROFS；写入尝试被拒绝 |

如实留白（也来自同一会话）：

- **Re:Kernel** 运行时已通过 NoActive 验证（见[真机截图](#真机截图)）；运行在源码补丁模式，不是 LKM
- **KPM/KPN** 实现了工具链钩子；尚未在真机实践
- **LineageOS**（官方 Ace6 构建）*预计*可用（树相同），**未确认** —— 测试机跑的是 Project Infinity X

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

仍待补充：**KPM/KPN**（尚未真机测试）。

---

## 功能开关

| 开关 | 默认 | 说明 |
|---|---|---|
| 🔗 **KernelSU** | `none` | ReSukiSU（内建 KSU）或无 |
| 🛡️ **SUSFS** | 关 | 增强的挂载/root 隐藏（需要 KSU） |
| ⚡ **lz4 1.10 + zstd 1.5.7** | 关 | 压缩性能（新算法，ARM64 NEON） |
| ⚡ **LZ4KD** | 关 | 额外的 lz4 变体，用于 zram |
| 🧪 **All zram algorithms** | 关 | 启用 `comp_algorithm` 中全部 zram 压缩器（含 lz4hc/842；容器/Droidspaces 场景有用） |
| 🛡️ **ZRAM writeback** | 关 | 将空闲/不可压缩的 zram 页写入后备设备（运行时需配置 `backing_dev`） |
| 📦 **Droidspaces** | 关 | 轻量 Linux 容器支持（standard/extend） |
| 🛡️ **Baseband Guard** | 关 | 内核级防格式化保护 |
| 🔒 **CVE patches** | 关 | GhostLock（CVE-2026-43499 + CVE-2026-53163）—— 上游现已包含，补丁已移除 |
| 🌐 **Better network** | 关 | ipset/iptables 高级网络支持 |
| 🚀 **BBR** | 关 | TCP 拥塞控制 |
| 🧩 **KPM/KPN** | 关 | KernelPatch Next（独立内核补丁支持） |
| 🔗 **Re:Kernel** | 关 | Freezer/NoActive binder 通知钩子 |
| 🏷️ **Kernel suffix** | 空 | 自定义版本后缀（如 `perf` → `6.6.139-4k-perf`） |
| ✍️ **Attribution** | 开 | 构建标签（user/host/REPO_NAME/AK3） |
| 📦 **Artifacts** | ak3 | `ak3`（刷机 zip）或 `all`（ak3 + Image + boot.img） |
| 🕐 **Build time** | 空 | 自定义构建时间戳（`KBUILD_BUILD_TIMESTAMP`）。CI 上所有构建时间戳通过 faketime 固定为 `2025-05-25` 以保证可复现 —— 自定义值会覆盖内核内嵌时间。本地（reproduce.sh）留空 = 当前 UTC |
| 💾 **Public ccache** | 关 | 上传构建缓存到 Release，加速重复构建 |
| 🔍 **ccache debug** | 关 | 上传 ccache 日志 |

---

## 功能详情

### 🔗 KernelSU (ReSukiSU)

- 克隆 [ReSukiSU](https://github.com/ReSukiSU/ReSukiSU)（完整历史 —— 版本号 = `30000 + 提交数 + 700`）
- 应用 7 个强制手动钩子（execveat/stat/faccessat/sys_read/sys_reboot/input/setresuid）
- 已验证版本 35046（`v4.1.0`）

### 🛡️ SUSFS

- 来自 [simonpunk/susfs4ksu](https://gitlab.com/simonpunk/susfs4ksu)（`gki-android15-6.6` 分支）
- 25 个主树文件 + 16 个 KernelSU 内部适配文件
- 包含全部 susfs 功能：sus_path、sus_mount、sus_kstat、uname 伪装、cmdline 伪装、open_redirect、sus_map、AVC 日志伪装

### 📦 Droidspaces

- `standard`：容器 + ntsync（NT 同步原语）
- `extend`：+ EVDI 虚拟显示、虚拟 HCI、systemd-coredump
- 内核配置：PID_NS/USER_NS/SYSVIPC/DEVTMPFS/POSIX_MQUEUE/namespaces

### 🔗 Re:Kernel

- **源码级集成**：netlink 服务器 + binder 钩子（reply/transaction/free_buffer_full）+ signal 钩子 —— LKM 方案试过之后放弃了（这棵树的符号不满足它需要的钩子）
- 全部包裹在 `#ifdef CONFIG_REKERNEL` 中 —— 关闭时零影响
- 针对 `lineage-23.2` 树（6.6.139）适配：`proc_ops` API、不同的 `binder_alloc`/`signal.c` 签名

> ⚠️ **已知坑 —— NoActive 白名单**：当 **Google 相册未进 NoActive 白名单**时，照片选择器（**相册与视频 Photos and videos** 权限 → **允许受限访问 Allow limited access** 模式）会一直空白加载，壁纸无法更换。深度睡眠/冻结挂起相册后，挂起进程不再消费 binder 事务：media.module 对相册的调用永不返回、其 binder 线程池被占死，选择器查询永远排队；同时 system_server 的 binder 线程会被其他被挂起的 Google 应用（GMS/地图/Gmail/Chrome）的 pending 同步事务占住。诊断：`adb shell su -c "cat /dev/binderfs/binder_logs/transactions"` 查找 `elapsed` 巨大的 pending 事务，用 `ps -A -o pid=,args=` 解析进程身份。解决：在 NoActive 里把 **Google 相册**（以及实际在用的 Google 应用）加进白名单——正确的冻结名单比 Re:Kernel 钩子更重要。

### 🛡️ Baseband Guard

- 来自 [cctv18/Baseband-guard](https://github.com/cctv18/Baseband-guard)
- 基于 LSM 的防格式化保护（阻止写入非用户分区）

### 🔒 GhostLock（CVE-2026-43499 + CVE-2026-53163）

两个漏洞现在都已由上游 `lineage-23.2` 覆盖：
- **CVE-2026-43499**：rtmutex `remove_waiter` NULL 防护 —— 上游 6.6.139 树自带（`scoped_guard`）
- **CVE-2026-53163**：`rtmutex_api.c` 中 proxy cleanup 的 `ret < 0` 修复 —— 上游已合入 `UPSTREAM: locking/rtmutex: Skip remove_waiter() when waiter is not enqueued`（2026-08-18 推送到 `lineage-23.2`）

独立的 `08_cve.patch` 因此已移除。

### ⚡ 压缩

- lz4 1.10（新库结构，ARM64 NEON 快速解压）
- zstd 1.5.7
- LZ4KD（来自 [ShirkNeko/SukiSU_patch](https://github.com/ShirkNeko/SukiSU_patch)）—— 用于 zram 的独立算法

---

## 使用方法

### 首次 Fork（一次性准备）

1. **Fork** 本仓库
2. **允许写入权限**：Settings → Actions → General → Workflow permissions → **Read and write**（Release 上传必需）
3. 先跑一次 **Upload AOSP Clang Toolchain** workflow —— 它会将官方工具链（clang 21.0.0 r563880c，约 1.5 GB）打包上传到你 fork 自己的 Release，构建从这里下载（没有 apt 备用源）
4. 向默认分支提交任意 commit，激活每周上游漂移检查

### 构建

1. 进入 **Actions** → **Build Ace6 Kernel** → **Run workflow**
2. 按需开关功能，点击 **Run workflow**
3. 从 run 的 **artifacts** 下载 AK3 zip（`release_enable` 开启时也可从 Release 下载）
4. 首次构建为冷编译（约 40 分钟）；之后构建复用 ccache（约 8 分钟）

### 刷入

1. **先备份当前槽位的 boot 分区** —— 用 OrangeFox（OFRP）或任意 recovery 的内置备份，或：
   `adb shell "dd if=/dev/block/by-name/boot_$(getprop ro.boot.slot) of=/sdcard/boot_backup.img"`
2. 通过 recovery（TWRP / OrangeFox / AOSP recovery）刷入 AK3 zip（`Kernel-Ace6-*.zip`）：Install → 选择 zip → 重启；或通过 KernelSU 管理器安装（Install → 刷镜像）。AnyKernel3 会自动刷**当前活动槽位**的 `boot` 分区（`boot_a` / `boot_b`，取决于当前运行槽）
3. **不要刷错分区**：本内核只进 `boot` —— 绝不是 `init_boot`，也不是非活动槽位
4. 卡 bootloop？恢复备份的官方 boot 镜像

### 工具链

- 使用 **AOSP Clang 21.0.0 (r563880c)** —— 与官方 OnePlus 内核构建完全相同的工具链
- 构建从**你自己仓库的 `toolchain-AOSP-Clang-21.0.0-r563880c` Release** 下载 —— 所以首次 fork 必须先跑上传 workflow；流水线里没有 apt.llvm.org 备用源

### 备注

- 默认 workflow 是**最小构建**（无 KSU、无功能）—— 需要什么开什么
- `kernel_suffix` 和 `build_time` 支持可复现、可识别的构建
- Attribution 默认 `Lingguang@kernel-builder` —— 可通过 `build_user`/`build_host` 修改，或用 `attribution_enable` 完全关闭

---

## 产物与 Release

本仓库产出三类东西 —— 别搞混：

| 产物 | 位置 | 可刷？ | 说明 |
|---|---|---|---|
| **AK3 zip**（`Kernel-Ace6-<用户>-ksu<版本>-<日期>.zip`） | run artifacts（14 天）/ Release（长期） | ✅ 可刷 | AnyKernel3 刷机包 —— 唯一需要刷的东西 |
| **`Image` + `boot.img`** | 仅 run artifacts，需 `artifact_mode = all` | ❌ 不可刷 | 开发者裸产物，无 ramdisk —— 刷了也没用 |
| **`toolchain-…` / `ccache-…` Release** | Releases 页 | ❌ 不可刷 | 构建基础设施（工具链 / ccache），不是内核 |

- Run 产物保留 **14 天**（`build.yml` 里的 `retention-days`）；Release 长期保留
- Release 标签形如 `kernel-20260803-115320-ksu35046` —— 该次构建参数的时间点快照
- 想让所有人都能拿到长期可刷包？开 **`release_enable`** —— release job 会发布带功能/版本表格和刷机说明的 AK3 zip

---

## 适配说明

本项目把多个来源的补丁（主要是 [cctv18/oppo_oplus_realme_sm8750](https://github.com/cctv18/oppo_oplus_realme_sm8750) 项目，针对一加官方 OKI 树）适配到 **Ace6 内核树**（`lineage-23.2`，内核 6.6.139）。关键适配：

- **补丁**拆分为独立开关（`patches/split/00-07, 09`）：`07_compile_fixes.patch` 无条件应用，其余由 workflow 功能开关控制（KSU/SUSFS/lz4/LZ4KD/Droidspaces/BBG/Re:Kernel）
- **新文件**（补丁无法创建的部分）放在 `patches/extra/` —— lz4/zstd 库、susfs.c、evdi、ntsync、Baseband-guard
- **Re:Kernel** 使用适配到 lineage-6.6.139 API 的源码钩子（netlink + binder/signal）
- **模块**来自 ROM 官方预编译 `vendor_dlkm` —— 无需重建模块树
- 部分一加官方独占功能（Fengchi scx 调度器、ADIOS IO 调度器）**未移植** —— 源码只存在于官方 OKI 树中

## 可复现性

- **LOCALVERSION 用真实 commit**（来自 GitHub API，因为源码是 zip 没有 .git）
- **`KBUILD_BUILD_TIMESTAMP`** 用于自定义/固定构建时间
- **ccache** 配 sloppiness（忽略文件 mtime/ctime）加速重复构建
- **Public ccache**（可选 `ccache_update`）：打包并上传缓存到 Release，近乎即时重建
- **上游漂移体检**：`check_upstream.sh`（以及每周 workflow）对最新 `lineage-23.2` 树逐个 dry-run 全部 9 个补丁 —— 漂移会以 review 请求 issue 的形式出现，而不是先以 bootloop 的形式出现
- 已验证：GitHub Actions 能产出与配置功能完全一致的、可开机的 AK3

**GitHub 免费额度现实核查**：Actions 每月 2,000 分钟 + 1 GB 缓存；本仓库的 ccache Release asset 约 630 MB、toolchain asset 约 1.5 GB。它们让重复构建很快，但也会消耗你的额度。大量或反复的本地工作，`reproduce.sh` 是免费路径 —— CI 是便利路径。

---

## 本地构建

仓库自带**跨机器本地构建脚本** —— `reproduce.sh`：

```bash
./reproduce.sh                          # 最小构建（无功能）
./reproduce.sh --ksu resukisu --susfs   # 带 ReSukiSU + SUSFS
./reproduce.sh --rekernel --bbg --lz4   # 更多功能
```

它会自动检测 clang 21（多个路径）、下载源码（或使用 `KERNEL_SRC`）、按开关应用补丁、拷贝额外文件、设置真实 commit，产出 AK3 zip。详见 `./reproduce.sh --help`。

**依赖**：clang 21（Arch：`pacman -S clang21 lld21 llvm21`；Ubuntu：apt.llvm.org；Fedora：`dnf install clang lld`）、git、patch、unzip、zip、curl、make。脚本从 `/etc/os-release` 检测发行版，缺 clang 21 时打印正确的安装命令。

**目录卫生**：所有中间产物（源码、打补丁后的树、AK3 打包目录）都在 `work/`；只有最终的刷机 zip 写入 `out/`。`./reproduce.sh --clean` 清空 `work/` 重新构建。仓库根目录不散落任何东西。

---

## 仓库结构

```
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md         # Bug 模板：ROM、开关、日志
│   │   └── bug_report_zh.md      # 中文 Bug 模板
│   └── workflows/
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
│   ├── selinux_perf/             # KSU 模块：静音 perf-HAL SELinux 拒绝日志
│   └── tcp-config/               # KSU 模块：TCP 算法/qdisc WebUI + nc fallback
│       └── webui-src/            # WebUI 构建源码（npm + esbuild）
├── ak3/                          # AnyKernel3 模板（tools/, META-INF/）
├── lib/                          # faketime 库 + ccache-ECS
├── LICENSE
├── check_upstream.sh             # 漂移体检：对最新树 dry-run 全部补丁
└── reproduce.sh                  # 本地构建脚本
```

---

## 路线图与寻求帮助

构建器本身**已完成并在一台设备上验证** —— 下面的缺口是真实的。每一项都是具体的帮忙方式，大多数不需要内核知识：

**寻找测试者** —— 尤其是官方 LineageOS（Ace6）用户：一份确认报告就能关掉下面最大的那个开放问题。

| 项目 | 状态 | 怎么帮 |
|---|---|---|
| **Re:Kernel 运行时验证** | ✅ 已通过 NoActive 验证（源码补丁模式） | —— |
| **KPM/KPN 真机测试** | ⏳ 工具链就绪，未实践 | 加载一个 KPM 模块，回报哪些正常/异常 |
| **LineageOS (Ace6) 确认** | 🤔 预计可用，未确认 | 在官方 LineageOS 上刷，用 [中文 bug 模板](.github/ISSUE_TEMPLATE/bug_report_zh.md) 开 issue |
| **其他 SM8750 设备** | 🧪 同树家族，未验证 | 自行测试风险自负 —— 先备份 `boot` |

**维护承诺**：作者跟进上游 `lineage-23.2` 和 ReSukiSU 的变化 —— 树漂移导致补丁打不上时，`reproduce.sh` 会在应用时响亮地失败；开 issue 就会被适配。

**参与**：详见 [CONTRIBUTING_zh.md](CONTRIBUTING_zh.md) 了解什么样的报告或 PR 更有用。

**版本**：Release 标签遵循 `kernel-<时间戳>-<功能标记>`（如 `kernel-20260803-115320-ksu35046`）—— 是那次构建的瞬时快照。目前没有升级路径承诺；标签是记录，可刷的 zip 才是交付物。

**计划中的功能**（都需要从官方 OKI 树移植 —— lineage 树里没有源码）：

- **Fengchi（风驰）scx 调度器** —— 一加官方的 sched_ext 调度器
- **ADIOS IO 调度器** —— 一加官方的定制块层调度器
- **官方 Ace6 120W SUPERVOOC 快充** —— 内核侧 vooc 协议栈；LOS ROM 的 vendor 侧可能不配合，真机充电效果是验证目标

不保证落地 —— 这是方向不是承诺；开工了才会更新这里的状态。

---

## 致谢

本项目建立在许多项目和开发者的工作之上。谢谢你们！

### 🏆 主要灵感与补丁来源

| 项目 | 用途 |
|---|---|
| [cctv18/oppo_oplus_realme_sm8750](https://github.com/cctv18/oppo_oplus_realme_sm8750) | **主要参考** —— workflow 设计、补丁结构、lz4/zstd/Droidspaces/BBG 集成、ccache-ECS、faketime |
| [Ace6-Development/android_kernel_oneplus_sm8750](https://github.com/Ace6-Development/android_kernel_oneplus_sm8750) | 内核源码（lineage-23.2） |
| [Ace6-Development/android_kernel_oneplus_sm8750-modules](https://github.com/Ace6-Development/android_kernel_oneplus_sm8750-modules) | 模块源码（符号链接目标） |
| [LineageOS/android_kernel_oneplus_sm8750-devicetrees](https://github.com/LineageOS/android_kernel_oneplus_sm8750-devicetrees) | 设备树源码 |

### 🧩 功能来源

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

### 🛠️ 工具与基础设施

| 项目 | 用途 |
|---|---|
| [Android AOSP clang prebuilts](https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86) | 官方工具链（r563880c） |
| [osm0sis/AnyKernel3](https://github.com/osm0sis/AnyKernel3) | AK3 刷机 zip 模板 |
| [cctv18/ccache-ECS](https://github.com/cctv18/ccache-ECS) | 专业内核构建缓存 |
| [ferstar/lz4-zstd](https://github.com/ferstar) | lz4/zstd 算法更新（经 cctv18） |
| [Xiaomichael](https://github.com/Xiaomichael) | lz4/zstd 移植（经 cctv18） |

### 🙏 特别感谢

- [**@cctv18**](https://github.com/cctv18) —— 整套构建流水线概念、补丁集成、ccache 优化思路
- [**@NullCode1337**](https://github.com/NullCode1337) —— Project Infinity X ROM 与 Ace6 内核开发
- **所有让自定义内核成为可能的上游内核/Android 项目**

---

## 许可证

[GPL-2.0](LICENSE)
