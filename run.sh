#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ -x .venv/bin/python ]]; then
    exec .venv/bin/python -m desktop_assistant
fi
exec python -m desktop_assistant
