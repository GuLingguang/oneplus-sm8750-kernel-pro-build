# Contributing

> **English** | [中文](CONTRIBUTING_zh.md)

This is a single-maintainer project. Keep reports and changes focused.

## Bugs

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md) — the three fields that
matter most are **ROM version**, **workflow toggles used**, and **logs**. A report without them
may be returned for completion before investigation.

Before opening one: flash the **minimal build** (all toggles off) once. If it boots, the bug is
in a feature toggle and the template's toggle list is how it gets isolated. If the minimal build
bootloops too, include that because it narrows the feature scope.

## Pull requests

- Keep the change to **one intent** per PR. Patch-splitting exists in this repo for a reason.
- English only in code, comments, and commit messages.
- Run `python3 scripts/ci.py` and `./reproduce.sh --help` to check the local rules; a PR
  that changes workflow logic should also be tested as a GitHub Actions run because it exercises
  the hosted runner.
- If the change touches patches: `patches/split/` is the authoritative source — regenerate or edit
  the split patches, keep `extra/` files in their kernel-relative paths, and confirm the split
  still applies in order (`patch -p1 -F3 --batch -f < patches/split/0*.patch`).

## License

GPL-2.0, same as the kernel. Contributed code uses the same license.

## Response time

The project is maintained part-time. Clear, single-purpose reports and PRs are reviewed first.
Project history prioritizes verified claims over unsupported conclusions.
