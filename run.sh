#!/usr/bin/env bash
set -euo pipefail
script_path="$(readlink -f -- "${BASH_SOURCE[0]}")"
cd "$(dirname -- "$script_path")"
if [[ -x .venv/bin/python ]]; then
    exec .venv/bin/python -m desktop_assistant
fi
exec python -m desktop_assistant
