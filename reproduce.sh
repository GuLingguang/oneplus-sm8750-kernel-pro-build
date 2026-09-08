#!/usr/bin/env bash
# Thin local front end. Parsing, locked source preparation, configuration,
# patching, build verification, packaging and manifest generation are shared
# with GitHub Actions in scripts/build.py.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$REPO_DIR/scripts/build.py" "$@"
