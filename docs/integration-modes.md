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
selection inputs. T06 now records a source-level contract and a clean
preparation run for the selected pairing; build and runtime acceptance remain
separate gates.

T06 reconstructed the official kernel patch plus the explicit ReSukiSU adaptation
on this kernel, including filename ownership/error paths, no_su and zygote_next
consumers. T07 must still verify every applicable signature, guard and consumer
before a build claim. The old legacy adapter is never applied automatically to
this candidate. The SUSFS profile is source-preparation-ready, while its build
and runtime gates remain open.

T06 has been executed with static evidence; T07 and the known faccessat runtime
risk remain unresolved until their dedicated checks.
The original legacy checkpoint remains available for comparison, not for a claim
of runtime safety or a verified flash-recovery package.
