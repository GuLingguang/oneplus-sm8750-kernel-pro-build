#!/usr/bin/env bash
# Thin local front end for the read-only device acceptance collector, so a run
# is one command from the repository root:
#
#   ./check_device.sh --build-out out/ace6-minimal-6.6 --soak-seconds 300
#
# It reads device state over adb and writes one evidence file here. It never
# flashes, installs or changes anything on the device.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

exec python3 "$SCRIPT_DIR/scripts/device.py" "$@"
