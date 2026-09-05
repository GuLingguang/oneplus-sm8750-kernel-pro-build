# SUSFS Inline contract for Ace6 6.6

This document records the source-level contract used by profile
`ace6-resukisu-susfs-inline-6.6`. It covers the locked source preparation
stage. Kernel compilation, boot images, and runtime mount hiding remain later
tasks (T25/T26).

## Locked inputs

| Input | Locked identity | Role |
| --- | --- | --- |
| Ace6 kernel | `cb967c26c2c5689108fa28d3c3be2aba6ba71f5f` | 6.6.142 target tree |
| ReSukiSU | `9d0ff6aea9e25fc7dd26f4643175a41f68375e5e` | native KernelSU SUSFS Inline implementation |
| SUSFS | `937215cb3a1b1f333d764c366c7a49972fa8e7a0` | official `gki-android15-6.6`, `SUSFS_VERSION v2.3.0` inputs |
| integration patch | `patches/integration/ace6-susfs-6.6.patch` | official 6.6 patch adapted only for the target `vma_data_pages()` context |

The lock links the complete ReSukiSU `kernel/` directory at
`drivers/kernelsu`, then adds the kernel Kconfig/Makefile sources. The
official `KernelSU/10_enable_susfs_for_ksu.patch` is intentionally not
applied: the locked ReSukiSU candidate already contains its native SUSFS
choice, declarations, definitions, and hooks. The legacy `02_ksu.patch` and
the old `const char __user **` faccessat/stat adapter are not inputs to this
profile.

## Interface and data-flow table

| Layer and location | Contract / type | Producer, consumer, and ownership rule |
| --- | --- | --- |
| `include/linux/susfs_def.h` | Defines `TIF_PROC_UMOUNTED=33`, `TIF_PROC_NO_SU=34`, and `TIF_PROC_UMOUNTED_FOR_ZYGOTE_NEXT=35`, with inline test/set/clear helpers. | The helpers operate on the current task's thread flags and are shared by ReSukiSU and patched VFS code. |
| ReSukiSU `kernel/hook/setuid_hook.c::handle_zygote_next_setresuid` | Sets `no_su`, `umounted`, and `umounted_for_zygote_next` for isolated processes, eligible app UIDs, and the configured webview zygote path. | This is the producer of the per-process state; the hook keeps the existing conditional webview behavior and then enters the SUSFS work path. |
| `fs/namespace.c::__lookup_mnt` | Reads `susfs_is_current_proc_umounted_for_zygote_next()` and filters candidate mounts to `mnt_id < DEFAULT_KSU_MNT_ID`. | This is the mount lookup consumer for the zygote-next flag. It returns a non-SUS mount or `NULL` before the original lookup path. Runtime behavior is deferred to T26. |
| `fs/open.c::do_faccessat` | `getname_flags()` returns `struct filename *`; the call is `ksu_handle_faccessat(int *, struct filename **, int *, int *)`. | `filename_lookup()` consumes the possibly rewritten filename. `putname(fname)` runs after lookup, including the `ERR_PTR` case handled by the kernel helper; retry re-enters the owned get/lookup/put sequence. |
| `fs/stat.c::vfs_statx` and `vfs_fstatat` | `ksu_handle_stat(int *, struct filename **, int *)` is declared and called with the same pointer-to-pointer type. | The stat callers own `getname_flags()`/`putname()` around `vfs_statx`; the handler only rewrites the owned `struct filename` and does not free it. Lookup errors leave through the existing error path. |
| `fs/exec.c::do_execveat_common` | The SUSFS branch passes `struct filename **` to `ksu_handle_execveat` and its sucompat wrapper. | The filename is already owned by the exec path; the hook is guarded by the `no_su` flag and the static key before the original flow. |
| ReSukiSU `kernel/feature/sucompat.h` and `sucompat.c` | Under `CONFIG_KSU_SUSFS`, declarations and definitions for faccessat/stat both use `struct filename **`. | Cross-CU signatures match the patched `fs/open.c` and `fs/stat.c` call sites. The `const char __user **` functions remain only in the inactive non-SUSFS/manual compatibility branch and are not selected by this profile. |
| ReSukiSU `kernel/runtime/ksud_integration.c::ksu_handle_vfs_fstat` | SUSFS-only fstat size hook is compiled under `CONFIG_KSU_SUSFS`. | It is part of the native candidate and is reached through the linked driver tree; no separate legacy adapter is overlaid. |
| `fs/Makefile` and ReSukiSU `kernel/Kconfig` | `susfs.o` is built when `CONFIG_KSU_SUSFS`; the Kconfig hook choice selects `KSU_SUSFS` and its SUSFS options. | The lock's driver link and kernel integration patch provide the cross-tree build declarations. Build validation is intentionally still pending. |

## Ownership and error-path checks

- `do_faccessat` obtains `fname` with `getname_flags`, calls the handler with
  `&fname`, performs `filename_lookup`, and calls `putname(fname)` exactly once
  for that attempt. `putname()` accepts the error pointer returned by
  `getname_flags`, so lookup errors do not leak the filename object.
- `vfs_statx` receives the filename owned by its caller. `vfs_fstatat` retains
  the existing `getname_flags`/`putname` pair; the handler does not change that
  ownership.
- The patched VFS call sites and the active SUSFS declarations/definitions do
  not use the legacy `const char __user **` faccessat/stat signature.
- The lock has one source for each responsibility: official SUSFS files are
  copied from the vendored commit, while the complete ReSukiSU driver is
  linked. No old KernelSU SUSFS enable patch is layered on top of native
  ReSukiSU integration.

The source-preparation evidence records the exact manifest, patch hashes,
prepared tree identities, and these static assertions. It does not claim a
successful kernel build or runtime mount hiding.
