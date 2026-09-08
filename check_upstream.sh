#!/usr/bin/env bash
set -euo pipefail

# Report-only adapter. It preserves --local for offline checks and fetches the
# candidate branch only when no local candidate is supplied. No lock or Issue
# is changed by this command.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPORT_DIR="${ACE6_DRIFT_REPORT_DIR:-$SCRIPT_DIR/work/_tmp/drift-report}"
ARGS=("--json-out" "$REPORT_DIR/drift-report.json"
      "--markdown-out" "$REPORT_DIR/drift-report.md"
      "--issue-draft" "$REPORT_DIR/drift-issue-draft.md")

if [[ "${1:-}" == "--ci" ]]; then
    shift
    ARGS+=("--ci")
fi

HAS_LOCAL=0
for argument in "$@"; do
    case "$argument" in
        --local|--candidate-kernel) HAS_LOCAL=1 ;;
    esac
done
if [[ "$HAS_LOCAL" -eq 0 ]]; then
    ARGS+=("--fetch-candidate")
fi
if [[ -n "${ACE6_MIRROR_PREFIX:-}" ]]; then
    ARGS+=("--mirror-prefix" "$ACE6_MIRROR_PREFIX")
fi

exec python3 "$SCRIPT_DIR/scripts/drift.py" "${ARGS[@]}" "$@"
