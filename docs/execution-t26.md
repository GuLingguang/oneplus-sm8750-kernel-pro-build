# T26：ReSukiSU + SUSFS 真机启动验收

日期：2026-09-06。记录时所有操作均在本地完成，未上传构建产物。后续仓库整理已在本地提交，仍未上传。

## 结果

| 检查项 | 结果 | 证据 |
| --- | --- | --- |
| 目标设备 | 通过 | `PLQ110 / OP6113L1`，目标代号 `ktm` |
| AK3 安装 | 通过 | 手动在 OFRP 刷入 ReSukiSU + SUSFS ZIP |
| 启动完成 | 通过 | `sys.boot_completed=1`，active slot `_a` |
| 实际内核身份 | 通过 | `/proc/version` 与启动 banner 为 `6.6.142-4k-gcb967c26c2c5+` |
| KSU | 通过 | `CONFIG_KSU=y`，root ADB context 为 `u:r:ksu:s0` |
| SUSFS | 通过 | `CONFIG_KSU_SUSFS=y`；`uname` 与真实 banner 的差异证明 spoof 生效 |
| KSU userspace | 通过 | `ksud 4.1.0-1338-g058cdc93 (uapi: 2)` |
| 基础硬件 smoke test | 通过 | Wi‑Fi validated、LTE in-service、触控注册、4 个 camera service device、43 个传感器、蓝牙/显示正常 |
| 电池与 zram | 通过 | 电池 health good / 99%；zram 使用 `lzo-rle`，6 GiB，swap active |
| 5 分钟稳定性初筛 | 通过 | 30/30 次采样保持 ADB、boot、内核 release、Wi‑Fi validated 和 zram 正常，未见可行动 panic/Oops |

## 边界

这次证明了刷写后能够启动、进入系统、恢复 root ADB，并确认 KSU/SUSFS
内核身份和基础稳定性初筛。相机实际拍摄、蜂窝数据吞吐、Wi‑Fi/蓝牙完整交互、触控、充电、休眠唤醒、长时间稳定性、
回滚和其他功能仍未完成验收，因此不把 profile 标记为 release-ready。

完整机器证据见 `docs/evidence/t26-runtime.json`；构建 manifest 位于
`out/resukisu-susfs-inline-6.6/build-manifest.json`。
