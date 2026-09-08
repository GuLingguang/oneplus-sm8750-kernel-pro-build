# ReSukiSU Manual Hook rules for Ace6 6.6

This document defines the source-preparation rules for
`ace6-resukisu-manual-6.6`. It is limited to the locked Ace6 6.6.142 tree and
the locked ReSukiSU candidate. A static rules check does not imply a kernel
build, boot, root-function, or device-runtime result.

## Locked inputs

| Input | Locked identity | Role |
| --- | --- | --- |
| Ace6 kernel | `cb967c26c2c5689108fa28d3c3be2aba6ba71f5f` | 6.6.142 target tree |
| modules | `7d5d39a539ddc2b53054e8fa7ae2b5890dccae54` | independent module source |
| devicetrees | `ebb25e3526ad84cc5a1090a5a9242f33ff087bf2` | device-tree source |
| ReSukiSU | `9d0ff6aea9e25fc7dd26f4643175a41f68375e5e` | KernelSU Manual Hook implementation |

The cumulative kernel steps are, in order:

1. `patches/split/07_compile_fixes.patch`
2. Link `drivers/kernelsu` to the locked `ReSukiSU/kernel` tree using
   `patches/integration/resukisu-kernel.link`.
3. Apply `patches/integration/ace6-resukisu-drivers.patch` to add the kernel
   Kconfig and Makefile entries.
4. Apply `patches/integration/ace6-resukisu-manual-6.6.patch`.

The profile does not apply SUSFS files, `patches/02_ksu.patch`, the SUSFS Inline
patch, or the legacy `00_ksu_hooks.patch`. Manual and SUSFS Inline are separate
Kconfig choices and are not combined.

## Hook table

| Kernel site | ReSukiSU symbol and type | Selection rule |
| --- | --- | --- |
| `kernel/sys.c::__sys_setresuid` | `int ksu_handle_setresuid(uid_t, uid_t, uid_t)` | Called when `CONFIG_KSU_MANUAL_HOOK_AUTO_SETUID_HOOK=n`; otherwise the 6.6 LSM hook owns setuid. |
| `fs/read_write.c::SYSCALL_DEFINE3(read)` | `int ksu_handle_sys_read(unsigned int, char __user **, size_t *)` | Called when `CONFIG_KSU_MANUAL_HOOK_AUTO_INITRC_HOOK=n`; otherwise the 6.6 LSM hook owns init-rc interception. |
| `drivers/input/input.c::input_event` | `int ksu_handle_input_handle_event(unsigned int *, unsigned int *, int *)` | Called when `CONFIG_KSU_MANUAL_HOOK_AUTO_INPUT_HOOK=n`; otherwise the input-handler path owns the hook. |
| `fs/exec.c::do_execveat_common` | `int ksu_handle_execveat(int *, struct filename **, void *, void *, int *)` | Required for every Manual configuration. The filename pointer type matches the non-SUSFS ReSukiSU branch. |
| `fs/open.c::do_faccessat` | `int ksu_handle_faccessat(int *, const char __user **, int *, int *)` | Required for every Manual configuration. The shared helper covers `faccessat` and `faccessat2`; no `struct filename` ownership conversion is performed. |
| `fs/stat.c::newfstatat` and `fstatat64` | `int ksu_handle_stat(int *, const char __user **, int *)` | Required for every Manual configuration; the pointer type matches the non-SUSFS branch. |
| `fs/stat.c::newfstat` | `void ksu_handle_newfstat_ret(unsigned int *, struct stat __user **)` | Required for the native stat return path. |
| `fs/stat.c::fstat64` | `void ksu_handle_fstat64_ret(unsigned long *, struct stat64 __user **)` | Required where the target architecture selects `__ARCH_WANT_STAT64` or `__ARCH_WANT_COMPAT_STAT64`. |
| `kernel/reboot.c::SYSCALL_DEFINE4(reboot)` | `int ksu_handle_sys_reboot(int, int, unsigned int, void __user **)` | Required for kernel 3.12+ layout, including this 6.6 tree. |

All declarations and calls are guarded by `CONFIG_KSU_MANUAL_HOOK`. The three
automatic options only guard their corresponding manual call; they do not remove
the required symbol from ReSukiSU. The hook return values are intentionally
handled according to the locked ReSukiSU signatures: the argument-mutating hooks
are called before the original kernel flow, while the stat return hooks run after
the kernel has filled the user buffer.

## Static symbol visibility

For the locked 6.6 candidate with `CONFIG_KALLSYMS_ALL=n`, the patch makes these
SELinux objects non-static so ReSukiSU's symbol lookup/fallback can find them:

- `security/selinux/selinuxfs.c::write_op`
- `security/selinux/selinuxfs.c::sel_handle_status_ops`
- `security/selinux/ss/services.c::security_dump_masked_av`
- `security/selinux/ss/services.c::context_struct_compute_av`

The change is limited to storage-class visibility; it does not add a second
implementation or alter the SELinux operation bodies.

## Incompatible and unselected paths

The locked Manual Hook checker must not find the incompatible legacy markers
`ksu_vfs_read_hook`, `is_ksu_transition`, or `ksu_handle_rename`. The profile also
does not promise Tracepoint Hook support. The `const char __user **` faccessat/stat
signatures are selected only for this non-SUSFS Manual profile; the SUSFS profile
uses its separate `struct filename **` interface.

## Evidence boundary

The T07 evidence records cumulative `git apply --check`, `git diff --check`, the
ReSukiSU `manual_hook_check.mk` across all eight automatic-option combinations,
the `static_export_check.mk`, and the isolated source-preparation manifest.
Build, `olddefconfig`, kernel boot, root operations, and runtime tests remain
unperformed and keep release disabled.
