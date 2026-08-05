# Contributing

> **English** | [中文](CONTRIBUTING_zh.md)

Small project, single maintainer, spare time. Keep it simple and it gets answered.

## Bugs

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md) — the three fields that
matter most are **ROM version**, **workflow toggles used**, and **logs**. A report without them
usually gets a "please fill in the template" reply instead of a fix.

Before opening one: flash the **minimal build** (all toggles off) once. If it boots, the bug is
in a feature toggle and the template's toggle list is how it gets isolated. If the minimal build
bootloops too, include that — it rules out half the patch stack.

## Pull requests

- Keep the change to **one intent** per PR. Patch-splitting exists in this repo for a reason.
- English only in code, comments, and commit messages.
- Run `./reproduce.sh --help` to see what the local path can verify; a PR that changes workflow
  logic should also be tested as a GitHub Actions run (that's the real environment).
- If the change touches patches: `patches/split/` is the source of truth — regenerate or edit
  the split patches, keep `extra/` files in their kernel-relative paths, and confirm the split
  still applies in order (`patch -p1 -F3 --batch -f < patches/split/0*.patch`).

## License

GPL-2.0, same as the kernel. Code you contribute inherits that.

## Response time

This is a one-person project with a day job. Issues get answered eventually; PRs with a clear
single intent get reviewed first. The project history shows what the maintainer cares about:
verified claims over confident ones.
