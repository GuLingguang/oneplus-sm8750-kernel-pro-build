# Selected integration candidates

| Component | Repository | Exact candidate |
| --- | --- | --- |
| Kernel | Ace6-Development/android_kernel_oneplus_sm8750 | `cb967c26c2c5689108fa28d3c3be2aba6ba71f5f` |
| ReSukiSU | ReSukiSU/ReSukiSU | `9d0ff6aea9e25fc7dd26f4643175a41f68375e5e` |
| Official SUSFS | simonpunk/susfs4ksu (GitLab), gki-android15-6.6 | `937215cb3a1b1f333d764c366c7a49972fa8e7a0`, header `v2.3.0` |

The ReSukiSU candidate retains the source identified by the historical successful
run's short SHA and the available full Git commit. This does not make that old
mixed integration acceptable. On 2026-09-05, upstream main was observed at
`f7829ddf548a18b851d653feb76b4a569b8fd2a4`; it is recorded separately and is not
automatically adopted.

At the chosen ReSukiSU commit, `kernel/feature/sucompat.h` declares SUSFS
`ksu_handle_faccessat(int *, struct filename **, int *, int *)`, and the non-SUSFS
path takes `const char __user **`. `kernel/Kconfig` declares the mutually
exclusive hook choice. Official SUSFS `README.md` describes its inline integration
and warns that patches are based primarily on official KernelSU. These are
selection inputs. T06 now records source-level rules and a clean
preparation run for the selected pairing; build and runtime acceptance remain
separate gates.

T06 reconstructed the official kernel patch plus the explicit ReSukiSU adaptation
on this kernel, including filename ownership/error paths, no_su and zygote_next
consumers. T07 now records the separate non-SUSFS Manual Hook rules and its
version-specific patch sequence. The old legacy adapter is never applied
automatically to this candidate. Both KSU profiles are source-preparation-ready;
their build and runtime gates remain open.

T06 and T07 have source-level static evidence. The known faccessat runtime risk,
kernel compilation, and device behavior remain unresolved until their dedicated
checks.
The original legacy checkpoint remains available for comparison, not for a claim
of runtime safety or a verified flash-recovery package.

T09 adds a separate Droidspaces standard path. The no-SUSFS variant uses the
42-option 6.6 configuration fragment, a target-specific SYSVIPC Android-kABI
adaptation and NTSYNC. The ReSukiSU container variant reuses the T07 Manual Hook
path and explicitly selects `CONFIG_KSU_SUSFS=n`; it does not inherit the SUSFS
Inline implementation. EVDI and the `ghost_task` vendor workaround remain
separate T11/T10 decisions. T11 now pins the EVDI files and power-mode UAPI,
adds that integration to both extend locks, and leaves userspace,
systemd-coredump and device checks as runtime warnings.

T12 now gives the Re:Kernel experimental path one built-in implementation,
formal Kconfig/Makefile wiring and shared Binder/binder_alloc/signal symbols.
T13 fixes the signal direction, Binder allocator reference and message-length
handling, and records a v1 wire definition. The profile remains blocked because
no pinned NoActive userspace receiver or runtime evidence is available; the
object build is not a full kernel or runtime claim.
