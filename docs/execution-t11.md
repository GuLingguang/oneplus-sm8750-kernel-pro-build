# Ace6 T11 执行记录：Droidspaces extend 6.6

日期：2026-09-06。范围是建立 extend 的独立能力清单，核对 EVDI/KABI 和
userspace 边界；没有把 EVDI、HCI 或 systemd-coredump 宣称为 standard 能力，
也没有进行完整内核、Android framework、真机或容器运行时验收。

## 结果

| 项目 | 结果 | 边界 |
| --- | --- | --- |
| standard → extend 继承 | 通过 | 两个 extend profile 保留 base features/capabilities，仅切换 droidspaces |
| EVDI 来源 | 已定位 | 14 个本地文件逐字匹配 `lindroid-drm-loopback@f15bc3e` |
| EVDI 目标对象 | 通过 | `CONFIG_DRM_LINDROID_EVDI=m`，仅 `evdi.o` |
| EVDI module/modpost | 受阻 | 临时输出没有目标 kernel `Module.symvers` |
| create-disp ABI | 不匹配 | userspace 候选调用 `SET_POWER_MODE(0x0f)`，内核 UAPI 没有它 |
| virtual HCI | 未验证 | 依赖 Android framework permission/uinput/device policy |
| systemd-coredump | 未锁定 | 依赖 userspace systemd/rootfs、socket 和 `core_pattern` |
| extend 状态 | blocked / experimental | 不进入 operational extend lock，不作 release claim |

## EVDI 源码与编译

本地 EVDI 文件来自 legacy inventory，但此前没有来源 commit。使用镜像
克隆的只读上游 `Linux-on-droid/lindroid-drm-loopback` 对比后，所有 14 个
源文件（含 UAPI/Kconfig/Makefile）与
`f15bc3ee6e9a90e85e70ef3da057f027c68cbefd` 完全匹配；该 commit 的 tree 是
`e6fa7935a0bbd44f27ccf41e0cf6b2f18feca568`。没有采用当前 master 的漂移内容。

在 T09 标准临时内核树中，仅应用 EVDI 的 DRM Kconfig/Makefile hunk，并接入
本地 EVDI 目录；`olddefconfig` 后设置 `CONFIG_DRM_LINDROID_EVDI=m`，命令
`make O=... ARCH=arm64 LLVM=1 drivers/gpu/drm/evdi/evdi.o` 通过。

```text
drivers/gpu/drm/evdi/evdi.o:
33c6d03ffa625b963682d8f9d45ec90d8a7f8cd6d6f3c92d2e7b14f2f2d27d1e
config:
95d0d7a8540f61c36a9eebe229d47a78571dae4cfad6ebd87adcaf2f51ca639b
```

尝试单独 `M=drivers/gpu/drm/evdi modules` 时，modpost 因临时树没有
`Module.symvers` 报未解析符号。这不是把失败隐藏成成功：当前证据只能记为
对象编译通过，完整模块链接仍需目标内核构建产出的符号表。

## userspace/API 审计

当前候选 snapshot 的 commit 已记录在机器证据中：`vendor_lindroid`
(`lindroid-22.1`)、`vendor_extra`/`libhybris`/`external_lxc` (`lindroid-21`)
以及 `create-disp` (`master`)。它们还没有按 Ace6 的 Android/framework/ROM
组合形成可复现的 userspace lock。

`create-disp` 在非 `TARGET_USES_REAL_HWC` 分支调用
`DRM_IOCTL_EVDI_SET_POWER_MODE`，而当前 EVDI UAPI 只到 `DRM_EVDI_VSYNC`
(`0x0e`)，内核驱动没有 `0x0f` 对应 ioctl。除非另有未锁定的 userspace
分支/编译宏或同步 kernel UAPI，否则启动后的 DPMS/display path 不能成立。

virtual HCI 依赖 Android 的 `VIRTUAL_INPUT_DEVICE` permission、uinput 和
framework/device policy；systemd-coredump 依赖目标 rootfs 的 systemd 服务、
socket activation 和 `kernel.core_pattern`。这些都不是内核 fragment 能自动
提供的内容。

## 真机需求

现在不需要真机测试：ABI 已经在静态层面出现明确缺口，先刷机只会把未锁定
的变量混在一起。待后续选定兼容 userspace、Ace6 ROM/framework/rootfs 并完成
完整 kernel/module build 后，才需要设备测试：EVDI card 创建/销毁、分辨率与
DPMS、触摸/键鼠输入、容器启动退出、联网、coredump 捕获及重启恢复。

详细机器证据位于 `docs/evidence/t11-droidspaces-extend.json`；profile
仍保持 experimental/blocked。
