#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' 'Python 3.10+ is required. Install it from https://www.python.org/downloads/' >&2
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
fi

".venv/bin/python" -m pip install --quiet --upgrade pip
".venv/bin/python" -m pip install --quiet -e .
exec ".venv/bin/python" -m spectracast --lan "$@"
