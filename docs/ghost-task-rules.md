# T10 `ghost_task` rules

Status: **disabled and blocked before source preparation**.

The legacy candidate is the `kernel/pid.c` portion of
`patches/split/05_droidspaces.patch`. It initializes a static object by copying
`init_task`, changes its displayed name and PID fields, and changes the global
`find_task_by_vpid()` result for callers identified as the module
`oplus_bsp_midas`. The candidate has not been added to an integration patch or
profile lock.

## Evidence boundary

The exact locked Ace6 kernel, modules and device-tree sources were searched at
the T10 inputs. Neither the kernel nor the modules source contains
`oplus_bsp_midas` or `ghost_task`, and the repository contains no device/ROM
mapping or original fault trace that identifies the affected scenario. The
legacy patch is therefore an uncorrelated vendor workaround, not a verified
requirement of the locked target.

The isolated candidate does compile as `kernel/pid.o` with the standard 6.6
configuration. This is only an object-level syntax/type result. It is not a
full kernel build, boot test, module test or runtime validation.

## Semantic rejection

`find_task_by_vpid()` is a globally exported GPL symbol used by 15 non-definition
kernel consumers, including futex, kcmp, network-namespace, capability,
cgroup, signal, scheduler, taskstats and tracing paths. Several consumers take
task references, lock task state, dereference `signal`, `mm`, `files`, `fs` or
`nsproxy`, and later release the task reference.

The workaround cannot establish the invariants those consumers require:

* `memcpy(&ghost_task, &init_task, sizeof(struct task_struct))` copies active
  task pointers, list links, namespace state and signal/sighand relationships;
* changing `usage`, `pid` and `tgid` does not create a valid PID object, RCU
  lifetime, task-list membership or reference-count ownership;
* returning `&init_task` when initialization is not ready is also not the
  requested missing-task result;
* module-name detection at a global lookup boundary is not a narrow driver-side
  compatibility API and can affect unrelated kernel paths reached by that
  caller.

Because a missing PID must remain `NULL`/`-ESRCH` unless a valid task lifetime
and ownership condition is proven, the candidate is rejected for generic Ace6,
Droidspaces and ReSukiSU profiles.

## Compatibility rule

The existing `ghost_task` input remains an explicit independent switch only so
the validator can reject it deterministically. When enabled,
`scripts/profile.py preflight` adds the T10 blocker and
`prepare_allowed` remains false. No lock includes the legacy hunk, and no
profile receives a generic container-support claim from it. Any future
device/ROM combination that genuinely needs this behavior stays experimental
and blocked.

Reconsideration requires all of the following: the exact `oplus_bsp_midas`
binary/source and device/ROM scope, an original reproducible fault trace, the
precise caller requirements, and a narrow fix that preserves normal missing-task
semantics and task lifetime rules. A driver-local API or an upstream-supported
compatibility change would be preferred over changing the global PID lookup.

Machine-readable evidence is in `docs/evidence/t10-ghost-task.json`; the
execution record is in `docs/execution-t10.md`.
