# Our On-Device Modifications

> **English** | [中文](CUSTOMIZATIONS_zh.md)

What *we* changed on the device itself — the layer that the kernel builder
repository does not own. Kernel-side build work (patch splits, vermagic,
ccache, …) lives in the builder repo and is not repeated here.

---

## 1. ZRAM writeback: hybridswap backing

### 1.1 What we did

Attach the vendor's `hybridswap` partition as zram's writeback backing device
at every boot, via the KSU module `azram-backing` (in `modules/`).

### 1.2 Why hybridswap

- 1024 MB partition, `/dev/block/by-name/hybridswap` (block device
  `/dev/block/sda13`), vendor-reserved for hybrid swap — **unused on this
  LOS-based ROM** (no fstab entry, no mount, no kernel config, no vendor
  reference; content is stale zeros only)
- zero `/data` space cost, zero loop devices — **all 44 loop nodes are taken
  by Android apex mounts**, so a file+loop backing is not possible on this
  device
- writeback capacity is capped by the backing size: 1 GB backing on a large
  zram caps writeback at 1 GB — fine for incompressible/idle page tails

### 1.3 The module and the division of labor

`azram-backing` does one thing: `swapoff → reset → attach backing`,
then stops. zram itself is Scene's job — `scene_swap_controller` rebuilds the
device (size, algorithm, swapon) and its "restore writeback" path re-attaches
our backing (it reads `backing_dev` before its own reset) — Scene was built
around this pattern:

| Owner | Owns |
|---|---|
| **azram-backing** (ours) | writeback device (backing = hybridswap), nothing else |
| **scene_swap_controller** (Scene) | zram: size/algorithm/rebuild/swapon + backing restore |
| **ZramWritebackBoost** (community) | writeback scheduling (screen/foreground/load aware) |
| **tcp-config** (ours) | runtime TCP congestion control & qdisc via WebUI |
| kernel config | default compressor lz4kd (choice flipped in our config) |

The `a` prefix orders our module first so the backing exists before Scene
rebuilds; Scene's config file is left untouched.

### 1.4 Kernel constraints we hit (zram_drv.c)

- `backing_dev` can only be set while zram is uninitialized — "Can't setup
  backing device for initialized device"
- `comp_algorithm` locks at initialization — set it before `disksize`
- a freshly reset zram has no swap signature — `mkswap` first, or swapon
  fails with EINVAL (Scene's startup.sh does the same)
- default compressor: flipped `CONFIG_ZRAM_DEF_COMP` in the builder config
  from LZORLE to LZ4KD, so init creates lz4kd zram with zero runtime setup

---

## 2. SELinux quieting (module `selinux_perf`)

**Problem**: `vendor_hal_perf_default` (the performance HAL) scans `/proc` at
boot and repeatedly hits `avc: denied` on the `ksu` / `kernel` domains —
constant log spam on every boot.

**Fix** (module `selinux_perf`, author GuLingguang):

```
allow vendor_hal_perf_default ksu dir search
allow vendor_hal_perf_default kernel dir search
allow vendor_hal_perf_default ksu file { read open getattr }
allow vendor_hal_perf_default kernel file { read open getattr }
```

**Verification**: after installing the module, the tail of dmesg shows no
perf-HAL denials (only low-frequency unrelated records remain).

---

## 3. TCP congestion control WebUI (module `tcp-config`)

A KernelSU WebUI page (`webroot/` + the `kernelsu` JS library, built with
esbuild — sources in `webui-src/`) offers three algorithms and a qdisc:

- **cubic** — Android default
- **bbr** — fq is recommended with BBR, but qdisc is an independent setting
- **kernel default** — read live from `/proc/config.gz`
  (`CONFIG_DEFAULT_TCP_CONG`)

qdisc (fq / fq_codel / pfifo_fast) is **independent**: changing the algorithm
never changes the qdisc, and vice versa (an early "auto" link that rewrote the
qdisc on algorithm change was removed as confusing). Both the WebUI and a
browser fallback channel share one core script (`webroot/apply.sh`): the WebUI
runs it via `kernelsu.exec()`, the fallback channel is a tiny `busybox nc -lk`
HTTP server on `:8090` (KSU's busybox has no httpd CGI and toybox has no httpd
at all, so raw `nc -lk -p 8090 -e handler.sh` is the server; the page falls
back to `fetch()` when the `ksu` bridge is absent). Changes apply to new
connections only, are saved to `/data/adb/tcpcfg.state`, and re-applied by
service.sh on boot (the page also restores the last selection on load).
`sysctl net.core.default_qdisc` works at runtime on this kernel (it updates
the `default_qdisc_ops` pointer) but has no compile-time config here — this
tree hardcodes `pfifo_fast_ops` in sch_generic.c instead of using
`CONFIG_DEFAULT_NET_SCH`.

---

## 4. Scene: left untouched (investigation notes)

**What we found**: Scene's `set_zram()` in the module's startup.sh is gated by
`[[ "$zram" == "true" ]] && [[ "$zram_size" != "" ]]` — and Scene's app had
written `comp_algorithm=lz4kd` to `/data/swap_config.conf` but never the
`zram`/`zram_size` fields, so the whole rebuild was skipped and init's
default (lzo-rle on the old kernel) persisted.

**Decision**: we considered patching `/data/swap_config.conf` (adding
`zram=true`/`zram_size`), tested it, then reverted — Scene is a third-party
module and we do not modify its config. Writeback is implemented
self-sufficiently in `azram-backing` (section 1), so Scene's zram function
stays disabled and the file stays as the Scene app wrote it
(`comp_algorithm=lz4kd` stays, it is unused while Scene's zram
setting is off).

---

## 5. NoActive freeze list: Google Photos must be whitelisted (2026-08-05)

**Symptoms**: Photo Picker (**Photos and videos** permission → **Allow limited
access** mode) hangs on an empty loading screen, occasionally works; system
wallpaper cannot be changed.

**Investigation** (`adb shell su -c "cat /dev/binderfs/binder_logs/transactions"`
— this kernel has binder debug enabled):
- media.module (`com.android.providers.media.module`) → Google Photos
  (`com.google.android.apps.photos`) sync transaction **never returned for
  46 minutes** (`elapsed 2802649ms`)
- system_server's binder threads parked on pending sync transactions to
  GMS / Maps / Gmail / Chrome / Nekogram (47–49 min each) — resolve pids with
  `ps -A -o pid=,args=`
- timeline matches NoActive deep sleep (`dozeType: locked`, suspends all
  non-whitelisted user apps 60 s after screen-off); after deep sleep exited,
  the processes were back (ps state `S`) but the pending transactions were
  **never consumed** — lost binder wake-up notifications

**Root cause**: Google Photos was not in NoActive's whitelist. Once deep sleep
suspended it, the suspended process stopped consuming binder transactions:
media.module's call into Photos never returns, its binder pool stalls and the
picker queues forever; system_server's pool gets parked the same way, stalling
system-wide binder calls (wallpaper). "Occasionally works" = the gap in which a
suspended process happened to get thawed and the backlog got consumed.

**Fix**: whitelist Google Photos in NoActive (along with GMS and the other
Google apps you actually use).

**Lesson**: **a correct freeze list matters more than the Re:Kernel hooks** —
the hooks handle "what binder does correctly when freezing happens", the list
decides "what gets frozen at all". Photos is a service provider the Photo
Picker chain depends on; once its process is not running, no hook can save the
pickup.
