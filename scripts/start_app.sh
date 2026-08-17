#!/usr/bin/env bash
#
# scripts/start_app.sh -- one-command launcher for the Gnosis desktop app.
#
# Uses conda's Python (KB_PYTHON wins; KB_CONDA_ENV selects an environment,
# default ``base``), exports it to the Electron main process, and starts the
# Vite + Electron dev stack. Run ``npm run app`` from the repo root, or this
# script directly.
#
#   bash scripts/start_app.sh          # start the app
#   bash scripts/start_app.sh --check  # print the chosen Python and exit

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP="$ROOT/desktop"

find_python() {
  if [[ -n "${KB_PYTHON:-}" ]]; then
    printf '%s\n' "$KB_PYTHON"
    return
  fi

  local conda_bin=""
  if command -v conda >/dev/null 2>&1; then
    conda_bin="$(command -v conda)"
  fi
  if [[ -z "$conda_bin" && -x /opt/anaconda3/bin/conda ]]; then
    conda_bin=/opt/anaconda3/bin/conda
  fi
  if [[ -n "$conda_bin" ]]; then
    local conda_base=""
    conda_base="$("$conda_bin" info --base 2>/dev/null || true)"
    if [[ -n "$conda_base" ]]; then
      local env_name="${KB_CONDA_ENV:-base}"
      if [[ "$env_name" == "base" ]]; then
        printf '%s\n' "$conda_base/bin/python3"
      else
        printf '%s\n' "$conda_base/envs/$env_name/bin/python3"
      fi
      return
    fi
  fi

  if [[ -x /opt/anaconda3/bin/python3 ]]; then
    printf '%s\n' "/opt/anaconda3/bin/python3"
    return
  fi
}

PYTHON="$(find_python)"
if [[ -z "$PYTHON" ]] || ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "error: no Python interpreter found; set KB_PYTHON=/path/to/python3.11" >&2
  exit 1
fi

read -r major minor <<< "$("$PYTHON" -c 'import sys; print(sys.version_info[0], sys.version_info[1])')"
if (( major < 3 || (major == 3 && minor < 10) )); then
  echo "error: Gnosis requires Python >= 3.10; $PYTHON is $major.$minor" >&2
  echo "set KB_PYTHON=/path/to/python3.11 and retry" >&2
  exit 1
fi

export KB_PYTHON="$PYTHON"

if [[ "${1:-}" == "--check" ]]; then
  echo "$PYTHON ($major.$minor)"
  exit 0
fi

if [[ ! -d "$DESKTOP/node_modules" ]]; then
  echo "desktop/node_modules missing; running npm install"
  npm --prefix "$DESKTOP" install
fi

exec npm --prefix "$DESKTOP" run dev
