# Decision log

## 2026-09-05 — M1 implementation begins

1. User instruction to begin the supplied plan authorizes the first T01–T05
   implementation batch; the older audit-only restriction is historical.
   Issue #3 comments/closure, merging and publishing remain outside this batch.
2. Preserve `c303fae1f308cd8c0a01b22f28b5bd34de6ab21a` as a legacy checkpoint.
   Work is isolated from the existing scratch trees that contain local changes.
3. Correct the ambiguity between workflow defaults (none/SUSFS off) and run
   33852164627 (explicit ReSukiSU/SUSFS on). Historical success covers only that
   run's enabled branch and does not establish runtime correctness.
4. Choose stdlib Python and JSON for the common normalization/preparation entry.
   No pip install, downloaded setup shell script or new floating dependency is
   needed for M1. The existing build entry points remain until T15.
5. Keep ReSukiSU's historical exact source as a candidate instead of silently
   following its advanced main branch. The official SUSFS source is pinned at
   v2.3.0; compatibility and replacement patch order remain gated by T06/T07.
6. Provide an explicit Manual candidate for KSU without SUSFS. Do not promise
   Tracepoint support. Containers default to no SUSFS; extend inherits standard.
7. Treat vendored feature content hashes as byte provenance only. Observed latest
   upstream commits are recorded as candidates, not invented origins of the old
   patches. Build environment/resource gaps keep T03 partially complete.
8. Source-preparation success, build success and runtime acceptance use separate
   statuses. No M1 output is a flashable kernel or a release recommendation.

## 2026-09-05 — T06 SUSFS Inline source preparation

1. Keep the complete locked ReSukiSU `kernel/` tree as a relative source link;
   do not copy or overlay a second KSU adapter into the kernel tree.
2. Use the official SUSFS `gki-android15-6.6` files and patch as the upstream
   input, adapting only the target tree's `vma_data_pages()` context.
3. Treat the `struct filename **` faccessat/stat signatures, filename ownership,
   thread flags and zygote-next mount lookup as one cross-tree contract. The
   inactive non-SUSFS/manual branch's `const char __user **` signatures are not
   selected by this profile.
4. Record source preparation and static contract evidence separately from
   compilation, olddefconfig, runtime mount hiding and publication. T07 remains
   the next gate for the remaining signature/guard/consumer checks.
