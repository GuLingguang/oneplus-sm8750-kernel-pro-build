# T21 — `selinux_perf` rule and effect boundary

日期：2026-09-07。完成本地规则审查、旧模块备份、禁用/启用两次重启对照；未
修改 SELinux 策略内容。

## Scope

Review the self-authored `selinux_perf` KernelSU module line by line. The
module is a policy exception for one source domain and two target object types;
it is not a generic `/proc` access grant or a performance-tuning switch.

## Reviewed rule

```te
allow vendor_hal_perf_default ksu dir search
allow vendor_hal_perf_default kernel dir search
allow vendor_hal_perf_default ksu file { read open getattr }
allow vendor_hal_perf_default kernel file { read open getattr }
```

| Field | Result |
| --- | --- |
| Source domain | `vendor_hal_perf_default` |
| Target object types | `ksu`, `kernel` |
| Directory permission | `search` only |
| File permissions | `read`, `open`, `getattr` only |
| Write/create/relabel/execute | Not granted |
| Path scope | Depends on the target ROM's compiled SELinux labels; not a blanket `/proc` rule |

## Device observation

- Target: OnePlus Ace 6 `PLQ110` / `OP6113L1`, Android 16.
- SELinux reports `Enforcing`.
- The installed v1.1 `sepolicy.rule` SHA-256 matches the reviewed local rule,
  and its `module.prop` SHA-256 matches the worktree.
- The device booted successfully both with the module disabled and with v1.1
  enabled. Each recent 5,000-record all-buffer `logcat` sample contained no
  `vendor_hal_perf_default` AVC denial.
- The sample did contain a PERFHAL poll-timeout message; it is not an AVC and
  is not evidence that this module improves performance.
- The same read-only label probes also generated unrelated `ksu`-domain
  `userfaultfd` AVC records; those are outside this module's target types.

## Boundary and remaining gate

The static permission review and the controlled disable/enable reboot comparison
are complete: both samples had zero matching AVC records and both boots passed.
This does not prove a performance benefit or causal necessity; the module remains
an observational/read-only policy exception and is not a performance switch.
