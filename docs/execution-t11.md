# Ace6 T11 执行记录：Droidspaces extend 6.6

初始审计日期：2026-09-06。适配更新：2026-09-09。范围包括 extend 的独立
能力清单、EVDI/KABI、userspace 边界和构建入口。完整 Image 已构建，Android
framework、真机和容器运行时仍未验收。

## 结果

| 项目 | 结果 | 边界 |
| --- | --- | --- |
| standard → extend 继承 | 通过 | 两个 extend profile 保留 base features/capabilities，仅切换 droidspaces |
| EVDI 来源 | 已锁定 | 14 个本地文件逐字匹配 `lindroid-drm-loopback@d3b85f3` |
| EVDI 目标对象 | 通过 | `CONFIG_DRM_LINDROID_EVDI=y`，生成 `built-in.a` |
| 完整 Image/AK3 | 通过 | 两个 extend profile 均以 30 线程完成并通过 `zip -T` |
| EVDI module/modpost | 不适用 | extend 选择内建驱动，不生成独立模块 |
| create-disp ABI | 已对齐 | userspace 与内核都定义 `SET_POWER_MODE(0x0f)` |
| virtual HCI | 未验证 | 依赖 Android framework permission/uinput/device policy |
| systemd-coredump | 未锁定 | 依赖 userspace systemd/rootfs、socket 和 `core_pattern` |
| extend 状态 | build-capable / experimental | 已进入 operational extend lock，仍不作 release claim |

## EVDI 源码与编译

使用镜像克隆的只读上游 `Linux-on-droid/lindroid-drm-loopback` 对比后，所有
14 个源文件（含 UAPI/Kconfig/Makefile）与
`d3b85f3251beae4bc8481538f37d13b7f30abde0` 完全匹配；该 commit 的 tree 是
`5e437ce3db2ccf3f73a4d5f876d716105886b736`。该版本包含 power-mode ioctl、
真实 dmabuf 导入修复及后续 EVDI 稳定性修复。

在 Ace6 主构建临时内核树中应用 EVDI 的 DRM Kconfig/Makefile hunk，接入
本地 EVDI 目录，并设置 `CONFIG_DRM_LINDROID_EVDI=y`。命令
`make ARCH=arm64 LLVM=1 LLVM_IAS=1 -j30 drivers/gpu/drm/evdi/` 通过。

```text
drivers/gpu/drm/evdi/built-in.a:
e59ca5e30081a3066a45b21f1d0437ec975ea0e6f8d61155edbde0e852e7d3e5
config:
73a7318679dfbaf40a7af077878f76ce35457b850600f7e29b61080901cff56e
```

当前证据覆盖 EVDI 目标目录的编译、静态链接、两个完整 Image 和 AK3 包。
设备加载与显示帧传递需要真机验收。

## userspace/API 审计

当前候选 snapshot 的 commit 已记录在机器证据中：`vendor_lindroid`
(`lindroid-22.1`)、`vendor_extra`/`libhybris`/`external_lxc` (`lindroid-21`)
以及 `create-disp` (`master`)。它们还没有按 Ace6 的 Android/framework/ROM
组合形成可复现的 userspace lock。

`create-disp` 在非 `TARGET_USES_REAL_HWC` 分支调用
`DRM_IOCTL_EVDI_SET_POWER_MODE`。当前锁定的 EVDI UAPI 将它定义为 `0x0f`，
驱动也注册了对应处理函数，静态 ABI 检查通过。Ace6 framework 构建和 DPMS
运行路径仍未验证。

virtual HCI 依赖 Android 的 `VIRTUAL_INPUT_DEVICE` permission、uinput 和
framework/device policy；systemd-coredump 依赖目标 rootfs 的 systemd 服务、
socket activation 和 `kernel.core_pattern`。这些都不是内核 fragment 能自动
提供的内容。

## 真机需求

内核构建已完成。选定兼容 userspace、Ace6 ROM/framework/rootfs 后，需要设备
测试：EVDI card 创建/销毁、分辨率与 DPMS、触摸/键鼠输入、容器启动退出、联网、
coredump 捕获及重启恢复。

详细机器证据位于 `docs/evidence/t11-droidspaces-extend.json`；两个 profile
保持 experimental，构建前置检查已放行，运行时仍未验收。
