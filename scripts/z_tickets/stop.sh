#!/usr/bin/env bash
# Signal the ticket runner to stop after the current ticket finishes.
# The runner (run_tickets.py) checks for this file between tickets and
# exits cleanly when it sees it. Remove the file to allow another run.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
touch "${HERE}/STOP"
echo "[stop.sh] created ${HERE}/STOP — runner will exit after the current ticket."
