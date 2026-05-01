#!/usr/bin/env bash
# Thin wrapper: run the ticket loop via uv so the inline PEP 723 script
# metadata in run_tickets.py picks the correct Python and dependencies
# (claude-agent-sdk) without you having to manage a virtualenv.
#
# Usage:
#   z_tickets/run_tickets.sh
#   touch z_tickets/STOP   # graceful halt after the current ticket
#
# Requires: uv (https://docs.astral.sh/uv/) and the `claude` CLI on PATH.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v uv >/dev/null 2>&1; then
  echo "[run_tickets.sh] ERROR: uv not found on PATH. Install: https://docs.astral.sh/uv/" >&2
  exit 127
fi

exec uv run "${HERE}/run_tickets.py" "$@"
