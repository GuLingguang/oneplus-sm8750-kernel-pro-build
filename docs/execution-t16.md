# Ace6 T16 execution record: identity and filename rules

Date: 2026-09-06. All changes remain local; no release or upload was performed.

## Result

The common builder now has one identity path for local and Actions builds:

- `build_user`, `build_host`, `kernel_suffix`, `build_time` and `tag` stay
  literal in the normalized config and build manifest. Control characters are
  rejected by the existing input rules.
- Kbuild environment values and `REPO_NAME` are passed/written by Python, not
  interpolated into shell or replacement strings. AK3's `kernel.string` uses a
  function replacement, so backslashes and replacement-looking text remain
  literal.
- Kernel localversion is `-4k-<suffix>` or `-4k-g<locked-commit-prefix>`.
  Filename components use an explicit ASCII-safe mapping recorded in the
  manifest; display text and filename text are not conflated.
- Attribution-off builds clear Kbuild user/host and KSU `REPO_NAME`, and use
  `Ace6` for the filename user component. `ksu<version>` is added only when
  `ksu_type` is not `none`.
- Release metadata is passed through environment variables in the workflow;
  raw tag/user text is not inserted into shell source.

The special-text dry-run covered Chinese text, spaces, `&`, `/`, backslashes,
quotes and `$(touch ...)`. No sentinel file was created, and the filename
mapping contained no slash. The unit suite passes **26/26**; syntax and
`git diff --check` pass.

This is an identity/configuration result only. Full Image, AK3, boot.img,
Release and runtime validation remain bounded by T15/T18/T25/T26.
