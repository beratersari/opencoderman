#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
if [[ ! -f "$HERE/agents/code-reviewer.md" ]]; then
  echo "[ERROR] agents/code-reviewer.md missing. Run this from the unpacked artifact or git checkout."
  exit 1
fi
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "[ERROR] python is not on PATH."
  exit 1
fi
exec "$PY" "$HERE/install.py" --root "$HERE"
