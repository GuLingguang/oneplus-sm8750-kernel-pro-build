# Ace6 T13 execution record: Re:Kernel semantics and protocol

Date: 2026-09-06. This task fixes the statically identifiable event-direction,
task-lifetime and message-length issues left by T12, and records a provisional
v1 wire definition. It does not claim NoActive or device runtime compatibility.

## Result

| Item | Result | Boundary |
| --- | --- | --- |
| signal direction | passed statically | frozen predicate uses target `p`; killer is `current`; destination is `p` |
| Binder allocator lifetime | passed statically | `find_get_task_by_vpid()` reference is released after event formatting |
| long-message handling | passed statically | `snprintf` required length is checked; payload API caps at 127 bytes |
| protocol definition | recorded | `ace6-rekernel-kv/v1`, unit `/proc` discovery, port 100 and event schemas |
| NoActive userspace match | unverified | no receiver/source/version was found in the workspace |
| object build | passed | four arm64 LLVM objects compile after T12 + T13 |
| runtime/full kernel | not tested | requires full image and named userspace/device; remains T25/T26 work |

## Code changes

The follow-up patch is
`patches/integration/ace6-rekernel-protocol-6.6.patch`, applied after
`ace6-rekernel-6.6.patch`. It does not modify the historical legacy patch.

Signal events now use `p` for the frozen target and report `current` as the
killer. The Binder allocator obtains a task reference with
`find_get_task_by_vpid()` and releases it with `put_task_struct()` after the
event path. All three callers check the result of `snprintf`; an event that
does not fit is not sent in truncated form.

## Verification boundary

The T13 patch passes `git apply --check` against the T12-prepared tree. The
same four objects compile with `ARCH=arm64 LLVM=1`; the normal host `bc`
package is installed because the kernel build generates `timeconst.h` with
that tool. `nm` still shows one Re:Kernel implementation and the three shared
API references. No runtime stress, fault injection, NoActive interaction,
full link or device test was performed.

Because the userspace counterpart is not locked, the profile remains
experimental/blocked even though the kernel-side semantic fixes are static
complete.
