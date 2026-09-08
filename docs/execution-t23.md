# T23 — report-only upstream workflow

## Workflow boundary

`.github/workflows/upstream-check.yml` runs the T22 checker on schedule or by
manual dispatch. Its only repository permission is `contents: read`. The job
uploads the JSON report, Markdown report, and generated Issue draft as an
artifact, including when the checker fails. It has no `issues: write` permission
and contains no automatic Issue mutation step.

The local wrapper and workflow both write reports to `work/_tmp/drift-report`,
so the uploaded artifact has a stable workspace-local path without using
system `/tmp`. The build workflow's temporary GKI helper is also under
`work/_tmp/gki`.

## Verification

| Check | Result |
| --- | --- |
| wrapper executable bit and `bash -n` | passed |
| `./check_upstream.sh --local work/minimal-6.6/src --profile ace6-minimal-6.6` | passed |
| default local report directory | `work/_tmp/drift-report` |
| report, Markdown, and Issue-draft files | generated |
| workflow permission review | `contents: read` only |
| automatic Issue mutation | absent |
| residual top-level `/tmp/ace6-*` after checks | 0 |

This task wires reporting and artifact handoff only. It does not promote a
profile to release-ready status and does not authorize lock updates.
