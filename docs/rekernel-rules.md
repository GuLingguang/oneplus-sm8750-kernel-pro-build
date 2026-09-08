# Re:Kernel integration rules

This document describes the T12 integration boundary for the experimental
`ace6-rekernel-experimental` profile. It does not claim that the NoActive
userspace protocol or a device runtime is validated.

## Kernel integration

The integration patch is
`patches/integration/ace6-rekernel-6.6.patch`. It is applied after the locked
ReSukiSU Manual integration. `CONFIG_REKERNEL` is a built-in boolean option,
not a module: `drivers/android/binder.c`, `drivers/android/binder_alloc.c` and
`kernel/signal.c` call the API directly.

`drivers/rekernel/rekernel.h` contains the shared constants and declarations
only. The single implementation is `drivers/rekernel/rekernel.c`, registered
through `drivers/rekernel/Kconfig` and `drivers/rekernel/Makefile`.

The ReSukiSU Manual base is a profile relationship, not a compile-time
dependency of the Re:Kernel driver. It supplies the selected root/hook
rules around this experimental variant; the driver itself depends on the
locked kernel's Binder IPC, networking, procfs and freezer facilities.

## State and lifecycle

The implementation has one `rekernel_server_lock`, one netlink socket, one
selected netlink unit and one proc status entry. `rekernel_server_start()`
serializes lazy initialization. A failed socket, `/proc/rekernel` directory or
unit entry creation removes all resources acquired by that attempt and returns
the state to `DOWN`, so a later call may retry.

`rekernel_send_netlink()` validates the message length before allocation and
checks the ready state while holding the same lock. This establishes the T12
single-state/concurrent-initialization rules. It does not yet establish the
full userspace protocol definition.

## T13 and runtime boundary

T13 corrects signal sender/target fields and the freeze predicate, keeps a task
reference across the Binder allocator lookup, and records the NoActive-facing
unit, port, message schema and long-message behavior in
`docs/rekernel-protocol-rules.md`. No matching NoActive receiver/version was
found in the workspace, and the full kernel build/device runtime is still open;
the source profile is therefore build-capable but remains experimental with a
T13/T26 warning. It is not release-ready.
