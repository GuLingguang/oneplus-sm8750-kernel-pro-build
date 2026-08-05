---
name: Bug report
about: Report a problem with a build — the more of the checklist you fill, the faster it can be debugged
title: "[Bug] "
labels: bug
assignees: ''

---

**Describe the problem**

What happened vs what you expected. Include anything unusual during flash or boot.

> **English** | [中文模板](bug_report_zh.md)

> Fill in what you can — the three fields that matter are ROM, workflow toggles, and logs.
> A one-line "it bootlooped" with those three answers is more useful than a paragraph without them.

**Build details (required)**

- **ROM**: e.g. `Project Infinity X v3.12` / `LineageOS 2026-08-02 nightly`
- **Device**: e.g. `OnePlus Ace 6 (ktm)`
- **Workflow inputs used**: ksu_type / susfs_enable / lz4_zstd / lz4kd_enable / show_all_algos / zram_writeback / droidspaces / baseband_guard / cve_patch / better_net / bbr_enable / kpm_enable / rekernel_enable / kernel_suffix / build_time / other
- **Kernel version**: output of `uname -r`
- **Flash method**: AK3 zip via recovery / fastboot / other

**Logs**

- If it boots: `adb logcat -b all > logcat.txt` + `dmesg > dmesg.txt`
- If it bootloops: which point it reaches (boot logo / system / recovery), and anything on screen
- GitHub Actions run ID if the build itself failed: link the run page

**Environment**

- Stock boot backed up? (`boot.img` — you did back it up, right?)
- What you flashed before this (previous kernel, stock, etc.)

**Checklist**

- [ ] I'm on a LineageOS-based ROM (ColorOS/OxygenOS is not supported)
- [ ] I backed up my `boot` partition
