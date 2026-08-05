---
name: Bug 报告（中文）
about: 报告构建问题 —— 清单填得越全，越容易定位
title: "[Bug] "
labels: bug
assignees: ''

---

**描述问题**

实际发生了什么 vs 预期。包括刷机或开机过程中的任何异常。

> 能填多少填多少 —— 最关键的三个字段是 ROM 版本、workflow 开关、日志。
> 一行"bootloop 了"带上这三样，比没有这三样的一段话有用得多。

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

- 备份了官方 boot 吗？（`boot.img` —— 你备份了吧？）
- 之前刷过什么（旧内核、官方包等）

**检查项**

- [ ] 我在 LineageOS 系 ROM 上（ColorOS/OxygenOS 不支持）
- [ ] 我备份了 `boot` 分区
