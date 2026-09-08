# Device-side modifications

> **English** | [中文](CUSTOMIZATIONS_zh.md)

This document records device-side changes. Kernel-side build work (patch
splits, vermagic, ccache, and related items) belongs to the builder repository
and is not repeated here.

---

## 1. ZRAM writeback: hybridswap backing

### 1.1 Device changes

The KSU module `azram-backing` is the guarded hand-off for attaching the
vendor's `hybridswap` partition as zram's writeback backing device on the
locked Ace6 target. The main profile now exposes a writable
`/sys/block/zram0/backing_dev`; v1.2 passed its identity, partition-use,
interface, and Scene-ownership checks, then attached `/dev/block/sda13`.
Those checks still precede any destructive transition.

### 1.2 Why hybridswap

- 1024 MB partition, `/dev/block/by-name/hybridswap` (block device
  `/dev/block/sda13`), vendor-reserved for hybrid swap — **unused on this
  LOS-based ROM** (no fstab entry, no mount, no kernel config, no vendor
  reference; content is stale zeros only)
- no `/data` space cost and no loop-device dependency — **all 44 loop nodes
  are taken by Android apex mounts**, so a file+loop backing is not possible
  on this device
- writeback capacity is capped by the backing size: 1 GB backing on a large
  zram caps writeback at 1 GB — suitable for incompressible or idle page tails

### 1.3 The module and the division of labor

`azram-backing` only performs the backing hand-off. It never selects the
compressor, chooses the zram size, or owns swapon. A reset is allowed only
after all guards pass, and a failed attach attempts to restore the recorded
compressor, size and swap priority. Scene remains the zram owner:
`scene_swap_controller` may rebuild the device only while its configuration
keeps `zram=false` and `zram_writeback=default` for this hand-off rule.

| Owner | Owns |
|---|---|
| **azram-backing** (project module) | writeback device (backing = hybridswap), nothing else |
| **scene_swap_controller** (Scene) | zram: size/algorithm/rebuild/swapon + backing restore |
| **ZramWritebackBoost** (community) | writeback scheduling (screen/foreground/load aware) |
| **tcp-config** (project module) | runtime TCP congestion control & qdisc via WebUI |
| kernel config | default compressor lz4kd (selected in the project config) |

The module checks `/data/swap_config.conf` at boot. If Scene is configured to
reset/rebuild zram or manage writeback itself, this module refuses to run;
module ordering alone is not treated as synchronization. `ZramWritebackBoost`
is a downstream consumer of writeback statistics/limits and must not reset
zram or replace the backing.

### 1.4 Kernel constraints (zram_drv.c)

- `backing_dev` can only be set while zram is uninitialized — "Can't setup
  backing device for initialized device"
- `comp_algorithm` locks at initialization — set it before `disksize`
- a freshly reset zram has no swap signature — `mkswap` first, or swapon
  fails with EINVAL (Scene's startup.sh does the same)
- the active main-profile kernel exposes a writable `backing_dev`; after the
  guarded hand-off the device reports a 1 GiB `/dev/block/sda13` backing, a
  6 GiB zram, active swap, and `lz4kd` as the default algorithm
- kernel-config defaults and the active runtime compressor are separate; the
  older inline profile was observed using `[lzo-rle]`, while the main profile
  uses the locked `lz4kd` default

---

## 2. SELinux permission exception (module `selinux_perf`)

The module is a narrow policy exception for a previously observed
`vendor_hal_perf_default` access path. `vendor_hal_perf_default` is the source
domain; `ksu` and `kernel` are target **object types**, not domains. The rule
does not grant generic `/proc` access and is not an unconditional performance
boost.

**Rules** (module `selinux_perf`, author GuLingguang):

```
allow vendor_hal_perf_default ksu dir search
allow vendor_hal_perf_default kernel dir search
allow vendor_hal_perf_default ksu file { read open getattr }
allow vendor_hal_perf_default kernel file { read open getattr }
```

The only granted permissions are directory `search` and file
`read/open/getattr`; there is no write, create, relabel, or execute permission.
Which paths receive the `ksu`/`kernel` labels is ROM policy dependent, so this
module must be reviewed against the target policy rather than described as a
blanket `/proc` fix.

**Current evidence**: on the PLQ110 / OP6113L1 Android 16 test device the
installed `sepolicy.rule` and `module.prop` match the reviewed worktree files.
SELinux is enforcing. The controlled disable/enable comparison completed two
boots with 5,000-record logcat samples and found no
`vendor_hal_perf_default` AVC in either phase. This does not establish a
performance benefit or prove that the module alone removed every historical
denial. See
[`docs/execution-t21.md`](execution-t21.md) and
[`docs/evidence/t21-selinux-perf.json`](evidence/t21-selinux-perf.json).

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
qdisc on algorithm change was removed as confusing). The WebUI invokes the
shared `webroot/apply.sh` through `kernelsu.exec()`. The old nc/browser
fallback is intentionally removed: a TCP socket cannot authenticate the
Android caller, so it would expose a root sysctl operation to an untrusted
network or local process. Changes apply to new connections only, are saved to
`/data/adb/tcpcfg.state` with an atomic mode-600 write, and re-applied by
service.sh on boot (the page also restores the last selection on load).
`sysctl net.core.default_qdisc` works at runtime on this kernel (it updates
the `default_qdisc_ops` pointer) but has no compile-time config here — this
tree hardcodes `pfifo_fast_ops` in sch_generic.c instead of using
`CONFIG_DEFAULT_NET_SCH`.

**Device boundary**: `tcp-config v1.1` replaced the old `v1.0` on the test
device. The unauthenticated `*:8090` listener is absent; direct `cubic/fq`
apply and a real WebUI click passed, and boot was restored. A local follow-up
only fixes the kernel-default display parser and remains uninstalled.

---

## 4. Scene: left untouched (investigation notes)

**Observed behavior**: Scene's `set_zram()` in the module's startup.sh is gated by
`[[ "$zram" == "true" ]] && [[ "$zram_size" != "" ]]` — and Scene's app had
written `comp_algorithm=lz4kd` to `/data/swap_config.conf` but never the
`zram`/`zram_size` fields, so the whole rebuild was skipped and init's
default (lzo-rle on the old kernel) persisted.

**Decision**: `/data/swap_config.conf` was not changed (the tested additions
were `zram=true`/`zram_size`) — Scene is a third-party
module and its configuration is not modified here. The main profile's kernel now exposes
writeback, so v1.2 can attach its backing without taking ownership of Scene's
size, algorithm, or swapon decisions. The hand-off was verified on device and
the active setup is 6 GiB zram with `lz4kd` and a 1 GiB `hybridswap` backing.

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

**Fix**: whitelist Google Photos in NoActive together with the required
Google applications.

**Conclusion**: the freeze list determines whether a required provider is
suspended; Re:Kernel hooks cannot compensate for an incorrect list. Photos is
a service provider required by the Photo Picker chain. The chain cannot
complete while that process is suspended.
