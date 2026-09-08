#!/usr/bin/env bash
# Online machine: fetch the OpenCode CLI into vendor/bin.
# Same as: python3 packaging/build_artifact.py --in-place
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
if [[ ! -f "$HERE/agents/code-reviewer.md" ]]; then
  echo "[ERROR] agents/code-reviewer.md missing. Run this from the git checkout."
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
echo "========================================"
echo "  OpenCoderman - vendor OpenCode CLI"
echo "========================================"
exec "$PY" "$HERE/packaging/build_artifact.py" --in-place --root "$HERE"
