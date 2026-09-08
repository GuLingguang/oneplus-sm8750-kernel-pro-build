---
name: Bug report
about: Report a build problem with the inputs and logs needed for diagnosis
title: "[Bug] "
labels: bug
assignees: ''

---

**Describe the problem**

Describe the observed behavior and the expected behavior. Include unusual
events during flashing or boot.

> **English** | [中文模板](bug_report_zh.md)

> Provide the ROM, workflow inputs, and logs whenever possible. These fields
> are required to reproduce or narrow down a build problem.

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

- Stock boot backed up? (`boot.img`)
- Previous flashed image or kernel (previous kernel, stock image, etc.)

**Checklist**

- [ ] I'm on a LineageOS-based ROM (ColorOS/OxygenOS is not supported)
- [ ] I backed up my `boot` partition
