# Ace6 T12 execution record: Re:Kernel integration

Date: 2026-09-06. This task rebuilt the formal kernel integration while
preserving the experimental boundary. It did not claim a complete kernel,
Android userspace, NoActive or device validation.

## Result

| Item | Result | Boundary |
| --- | --- | --- |
| single implementation | passed | state, proc endpoint and netlink functions live in one `.c` |
| formal Kconfig/Makefile | passed | `CONFIG_REKERNEL` is a built-in option under `drivers/` |
| normalized configuration | passed | profile feature remains `rekernel=true`; final isolated config has `CONFIG_REKERNEL=y` |
| shared callers | passed | binder, binder_alloc and signal resolve the same three symbols |
| initialization lock | static passed | one mutex guards ready state and socket/proc setup; no runtime stress test |
| failure cleanup | static passed | partial proc/netlink setup is removed and state returns to `DOWN`; no fault injection |
| object build | passed | four arm64 LLVM objects compiled against the T09 ReSukiSU tree |
| full kernel/modpost | not run | target `Module.symvers`, final image and packaging remain T25/T18 work |
| protocol/RCU/runtime | blocked | deferred to T13 and T26 |

## Integration changes

The new locked integration patch is
`patches/integration/ace6-rekernel-6.6.patch`. It leaves the historical
`patches/split/09_rekernel.patch` untouched for comparison and replaces its
per-translation-unit header implementation with:

- a declarations-only `rekernel.h`;
- one built-in `rekernel.c` implementation;
- `drivers/rekernel/Kconfig` and `drivers/rekernel/Makefile`;
- the Binder, Binder allocator and signal call sites using the shared API.

The profile still inherits `ace6-resukisu-manual-6.6`. This is a profile-level
relationship; `REKERNEL` does not silently depend on KSU symbols in the kernel
driver.

## Isolated verification

On the locked arm64 source with T09 preparation already present, after
`olddefconfig` and `CONFIG_REKERNEL=y`, the following targets compiled:

```text
drivers/rekernel/rekernel.o
drivers/android/binder.o
drivers/android/binder_alloc.o
kernel/signal.o
```

`nm` shows `rekernel_server_start`, `rekernel_send_netlink` and
`rekernel_line_is_frozen` defined only by `rekernel.o` and referenced by all
three callers. The patch passes forward application before the isolated build
and reverse application after it. The host needed the single `bc` package for
the kernel's generated `timeconst.h`; no project file or external source was
modified by that setup.

## Remaining gate

T13 must fix event direction/field semantics, the Binder allocator task
lifetime after RCU, and the userspace protocol definition. T26 later needs a
named device/ROM/NoActive userspace combination and reproducible runtime logs.
No real-device test is requested at this T12 stage.
