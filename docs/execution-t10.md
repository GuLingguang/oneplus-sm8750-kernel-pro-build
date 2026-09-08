# Ace6 T10 执行记录：ghost_task vendor workaround

日期：2026-09-06。范围是隔离评估 legacy `ghost_task` workaround，不把它
接入标准 Droidspaces、ReSukiSU 或其他 profile。没有进行完整内核、启动、
真机、容器或运行时验收。

## 结果

| 项目 | 结果 | 边界 |
| --- | --- | --- |
| vendor/source 关联 | 未建立 | 精确锁定 kernel/modules 没有 `oplus_bsp_midas` 或 `ghost_task` |
| 原始故障证据 | 未发现 | 仓库和精确源树没有设备/ROM 映射或可复现 trace |
| ghost hunk 编译 | 通过 | 仅 `kernel/pid.o`，不是完整 kernel build |
| 语义规则 | 拒绝 | 全局 PID 查询返回伪造 `task_struct`，生命周期/字段不成立 |
| profile 接入 | 停用 | 不加入 integration patch 或 lock；`ghost_task=true` 保持 preflight blocker |
| runtime/release | 未测试 / 禁止 | `release_allowed=false` |

## 锁定输入

| Source | Commit |
| --- | --- |
| Ace6 kernel | `cb967c26c2c5689108fa28d3c3be2aba6ba71f5f` |
| modules | `7d5d39a539ddc2b53054e8fa7ae2b5890dccae54` |
| devicetrees | `ebb25e3526ad84cc5a1090a5a9242f33ff087bf2` |

Candidate patch: `patches/split/05_droidspaces.patch`, SHA-256
`ddf0aff68fa4e10cc405812b3191960b29a2c99c278a3c975f77e44ca25935eb`.
Only its `kernel/pid.c` path was applied to a disposable T09 standard tree.

## 审计结论

Legacy hunk performs these operations:

1. copies all of `init_task` into a static `ghost_task`;
2. changes `comm`, `pid`, `tgid` and usage-like counters;
3. hooks the globally exported `find_task_by_vpid()`;
4. returns the fake object, or `&init_task` before initialization, only when
   `_RET_IP_` resolves to `oplus_bsp_midas`.

The exact locked source has 16 files containing `find_task_by_vpid`, including
the definition and 15 consumers. Critical consumers use the result in ways
that require a real task: futex obtains a task reference and accesses signal
state, kcmp locks `signal->exec_update_lock` and later calls
`put_task_struct`, while network-namespace lookup locks the task and reads
`nsproxy`. A copied static object cannot provide those PID, RCU, list,
reference-count, namespace and signal invariants.

The absence of the named vendor module and of a reproducible fault means there
is no evidence to define a narrower compatibility boundary. The safe local
result is deactivation; no generic fallback implementation is included.

## Isolated build evidence

The disposable tree was built with `ARCH=arm64`, `LLVM=1`, the standard T09
output configuration and `make O=... kernel/pid.o`. The normal target completed
with only pre-existing duplicate `dtbs` recipe warnings. The resulting object
hash is:

```text
kernel/pid.o: 9eca08c6d0853e9e079d88eccda92249460a59e4e16b93fb9e4b3244efaba6c6
```

The object contains `ghost_task`, `init_ghost_task` and
`find_task_by_vpid`; this confirms compilation only. Runtime and full-kernel
claims remain open.

## Gate and follow-up

`scripts/profile.py preflight` already maps `ghost_task` to T10. With the
feature enabled it reports `prepare_allowed=false` and the blocker
`ghost_task: integration/configuration rule pending T10`. No profile lock
was changed for this task. Reconsideration needs the exact vendor binary/source,
device/ROM scope, original trace and a driver-local or otherwise lifetime-safe
rule.

Detailed machine-readable evidence is in
`docs/evidence/t10-ghost-task.json`.
