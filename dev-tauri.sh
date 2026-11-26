#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/apps/desktop"

command -v npm >/dev/null || { echo "Node.js 22 is required." >&2; exit 1; }
command -v cargo >/dev/null || { echo "Rust is required." >&2; exit 1; }

if [[ ! -d node_modules ]]; then
  if [[ -f package-lock.json ]]; then npm ci; else npm install; fi
fi
npm run tauri dev
