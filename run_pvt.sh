#!/usr/bin/env bash
# run_pvt.sh — wrapper to run the PVT CLI, activating a virtualenv if present.
#
# Usage:
#   ./run_pvt.sh --gor 850 --p_sep 815 --t_sep 145 --z_sep 0.855 --v_cell 300
#   ./run_pvt.sh --help
#
# Virtualenv detection order:
#   1. .venv/   (local to the PVT-Calculator directory)
#   2. venv/    (common alternative name)
#   3. Falls back to whatever `python` / `python3` is on $PATH

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    # shellcheck source=/dev/null
    source "$SCRIPT_DIR/.venv/bin/activate"
elif [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    # shellcheck source=/dev/null
    source "$SCRIPT_DIR/venv/bin/activate"
fi

# Prefer python3 if available, fall back to python
if command -v python3 &>/dev/null; then
    PYTHON=python3
else
    PYTHON=python
fi

exec "$PYTHON" "$SCRIPT_DIR/cli.py" "$@"
