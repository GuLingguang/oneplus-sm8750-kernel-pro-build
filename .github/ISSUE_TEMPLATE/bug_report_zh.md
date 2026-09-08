---
name: Bug 报告（中文）
about: 报告构建问题，并提供定位所需的构建输入和日志
title: "[Bug] "
labels: bug
assignees: ''

---

**描述问题**

请描述实际行为和预期行为，并记录刷机或开机过程中的异常。

> 请尽量提供 ROM 版本、workflow 开关和日志。这些字段用于复现或缩小
> 构建问题的范围。

**构建详情（必填）**

- **ROM**：如 `Project Infinity X v3.12` / `LineageOS 2026-08-02 每夜版`
- **设备**：如 `OnePlus Ace 6 (ktm)`
- **用到的 workflow 开关**：ksu_type / susfs_enable / lz4_zstd / lz4kd_enable / show_all_algos / zram_writeback / droidspaces / baseband_guard / cve_patch / better_net / bbr_enable / kpm_enable / rekernel_enable / kernel_suffix / build_time / 其他
- **内核版本**：`uname -r` 的输出
- **刷入方式**：recovery 刷 AK3 zip / fastboot / 其他

**日志**

- 能开机：`adb logcat -b all > logcat.txt` + `dmesg > dmesg.txt`
- bootloop：卡在哪个阶段（boot logo / 系统 / recovery），屏幕上有什么
- 构建本身失败：附 GitHub Actions run 的链接

**环境**

- 是否备份官方 boot（`boot.img`）
- 之前刷过什么（旧内核、官方包等）

**检查项**

- [ ] 我在 LineageOS 系 ROM 上（ColorOS/OxygenOS 不支持）
- [ ] 我备份了 `boot` 分区
