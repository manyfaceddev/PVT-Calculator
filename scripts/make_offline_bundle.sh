#!/usr/bin/env bash
# scripts/make_offline_bundle.sh — Build a self-contained offline install
# bundle for a locked-down PC with no internet access.
#
# The target PC is assumed to have (or be able to get) a plain Python 3.12
# with no admin rights and no preinstalled Streamlit. This script produces
# a folder that lets that PC install the whole project — including the
# streamlit and openpyxl packages and their full transitive dependency
# closure — with `pip install --no-index`, i.e. zero network access.
#
# Run this on any machine WITH internet access (it downloads wheels from
# PyPI). Copy the resulting dist/pvt-offline-<platform>/ folder to the
# target PC (USB stick, network share, etc.) and follow its INSTALL.txt.
#
# Usage:
#   bash scripts/make_offline_bundle.sh [PLATFORM_TAG] [--dev]
#
#   PLATFORM_TAG   A pip wheel platform tag for the TARGET machine, e.g.
#                  win_amd64, manylinux2014_x86_64, macosx_11_0_arm64.
#                  Omit to build for the CURRENT machine (native download;
#                  no cross-platform flags are passed to pip).
#   --dev          Also download the project's [dev] extra (pytest,
#                  pytest-cov, ruff, mypy) into wheels/. Omitted by default
#                  — the default bundle carries runtime dependencies only.
#
# Examples:
#   bash scripts/make_offline_bundle.sh                  # bundle for this machine
#   bash scripts/make_offline_bundle.sh win_amd64         # bundle for a Windows target
#   bash scripts/make_offline_bundle.sh manylinux2014_x86_64 --dev

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

fail() {
    echo "make_offline_bundle.sh: ERROR: $*" >&2
    exit 1
}

# ── Argument parsing ─────────────────────────────────────────────────────
PLATFORM_TAG=""
DEV=0

for arg in "$@"; do
    case "$arg" in
        --dev)
            DEV=1
            ;;
        -h|--help)
            sed -n '2,29p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        -*)
            fail "unknown option: $arg (usage: make_offline_bundle.sh [PLATFORM_TAG] [--dev])"
            ;;
        *)
            if [ -n "$PLATFORM_TAG" ]; then
                fail "only one platform tag may be given (got '$PLATFORM_TAG' and '$arg')"
            fi
            PLATFORM_TAG="$arg"
            ;;
    esac
done

PYTHON_VERSION_TAG="312"

# ── Tooling checks ───────────────────────────────────────────────────────
command -v python3 >/dev/null 2>&1 \
    || fail "python3 is not on PATH."
command -v git >/dev/null 2>&1 \
    || fail "git is not on PATH (needed for 'git archive')."
python3 -c "import pip" >/dev/null 2>&1 \
    || fail "pip is not importable by python3 (python3 -m pip). Install pip first."

# This project requires Python >=3.12 (pyproject.toml). For the native
# (no PLATFORM_TAG) download path we don't pass --python-version to pip,
# so the ambient interpreter's own ABI is what gets downloaded -- it must
# actually be 3.12, or wheels for compiled deps (numpy, pandas, pyarrow,
# ...) would be built for the wrong ABI and fail to install on a 3.12
# target.
PY_MM="$(python3 -c 'import sys; print(f"{sys.version_info[0]}{sys.version_info[1]}")')"
if [ "$PY_MM" != "$PYTHON_VERSION_TAG" ]; then
    fail "this script must be run with Python 3.12 on PATH as 'python3' (found $(python3 --version 2>&1)). Install/select a Python 3.12 interpreter and re-run."
fi

PYPROJECT="$REPO_ROOT/pyproject.toml"
[ -f "$PYPROJECT" ] || fail "pyproject.toml not found at $PYPROJECT"

# ── Resolve platform label for the output directory name ────────────────
if [ -n "$PLATFORM_TAG" ]; then
    PLATFORM_LABEL="$PLATFORM_TAG"
else
    PLATFORM_LABEL="$(python3 -c 'import platform; print(f"{platform.system().lower()}-{platform.machine().lower()}")')"
fi

BUNDLE_NAME="pvt-offline-$PLATFORM_LABEL"
DIST_DIR="$REPO_ROOT/dist"
BUNDLE_DIR="$DIST_DIR/$BUNDLE_NAME"
WHEELS_DIR="$BUNDLE_DIR/wheels"
SRC_DIR="$BUNDLE_DIR/src"
INSTALL_TXT="$BUNDLE_DIR/INSTALL.txt"

echo "make_offline_bundle.sh: building offline bundle"
echo "make_offline_bundle.sh:   platform : ${PLATFORM_TAG:-<current machine: $PLATFORM_LABEL>}"
echo "make_offline_bundle.sh:   dev extra: $([ "$DEV" -eq 1 ] && echo yes || echo no)"
echo "make_offline_bundle.sh:   output   : ${BUNDLE_DIR#"$REPO_ROOT"/}"

rm -rf "$BUNDLE_DIR"
mkdir -p "$WHEELS_DIR" "$SRC_DIR"

# ── Extract the dependency closure to download from pyproject.toml ──────
# Runtime deps (project.dependencies) always; [dev] extra only with --dev;
# plus the [build-system] backend (setuptools) and "wheel", both needed
# offline to install the local project from source on the target PC.
DEPS_FILE="$(mktemp)"
trap 'rm -f "$DEPS_FILE"' EXIT

python3 - "$PYPROJECT" "$DEV" > "$DEPS_FILE" <<'PYEOF'
import sys
import tomllib

path, want_dev = sys.argv[1], sys.argv[2] == "1"
with open(path, "rb") as f:
    data = tomllib.load(f)

project = data["project"]
deps = list(project.get("dependencies", []))
if want_dev:
    deps += list(project.get("optional-dependencies", {}).get("dev", []))

# Build-backend requirements (PEP 517/518): needed to install/build the
# local project from source with no network access on the target PC.
deps += list(data.get("build-system", {}).get("requires", []))
deps.append("wheel")

for d in dict.fromkeys(deps):  # de-dup, preserve first-seen order
    print(d)
PYEOF

DEPS=()
while IFS= read -r line; do
    [ -n "$line" ] && DEPS+=("$line")
done < "$DEPS_FILE"

[ "${#DEPS[@]}" -gt 0 ] || fail "no dependencies resolved from $PYPROJECT"

echo "make_offline_bundle.sh: dependency closure to download:"
printf '  - %s\n' "${DEPS[@]}"

# ── Download wheels (full transitive closure, binary-only) ──────────────
# --only-binary=:all: is used unconditionally (not just for cross-platform
# downloads): a locked-down target PC almost never has a C compiler, so an
# sdist that pip would otherwise silently fall back to building is exactly
# the kind of failure this bundle exists to avoid. If a dependency has no
# prebuilt wheel for the requested platform/Python combination, pip fails
# loudly here instead of shipping something unbuildable.
PIP_DOWNLOAD_ARGS=(-m pip download --dest "$WHEELS_DIR" --only-binary=:all:)
if [ -n "$PLATFORM_TAG" ]; then
    PIP_DOWNLOAD_ARGS+=(
        --platform "$PLATFORM_TAG"
        --python-version "$PYTHON_VERSION_TAG"
        --implementation cp
        --abi "cp${PYTHON_VERSION_TAG}"
    )
fi

echo "make_offline_bundle.sh: running: python3 ${PIP_DOWNLOAD_ARGS[*]} <deps...>"
python3 "${PIP_DOWNLOAD_ARGS[@]}" "${DEPS[@]}" \
    || fail "pip download failed -- check internet access on this (build) machine, and that '$PLATFORM_TAG' is a valid pip platform tag with wheels available for every dependency."

WHEEL_COUNT="$(find "$WHEELS_DIR" -type f | wc -l | tr -d ' ')"
[ "$WHEEL_COUNT" -gt 0 ] || fail "no files landed in $WHEELS_DIR after pip download"
echo "make_offline_bundle.sh: downloaded $WHEEL_COUNT distribution file(s) to wheels/"

# ── Archive the source tree (repo at HEAD, no .git, no untracked cruft) ──
git -C "$REPO_ROOT" archive HEAD | tar -x -C "$SRC_DIR" \
    || fail "'git archive HEAD' failed"
[ -f "$SRC_DIR/pyproject.toml" ] \
    || fail "git archive did not produce a valid source tree (pyproject.toml missing under src/)"

# ── INSTALL.txt ───────────────────────────────────────────────────────────
BUILD_DATE="$(date -u +%Y-%m-%d)"
DEV_NOTE="Runtime dependencies only (streamlit, openpyxl, and their full transitive closure)."
if [ "$DEV" -eq 1 ]; then
    DEV_NOTE="Runtime dependencies PLUS the [dev] extra (pytest, pytest-cov, ruff, mypy)."
fi

cat > "$INSTALL_TXT" <<EOF
PVT Lab Platform -- Offline Installation (locked-down PC)
===========================================================

Built:    $BUILD_DATE (UTC)
Platform: ${PLATFORM_TAG:-$PLATFORM_LABEL (current build machine)}
Python:   3.12 (cp312)
Contents: $DEV_NOTE

This folder is self-contained. Nothing below touches the network -- every
command uses pip's --no-index flag, which makes pip refuse to contact
PyPI at all, so a missing file fails loudly instead of silently "working"
on a machine that happens to have internet.

  wheels/   Every Python package this project needs (streamlit, openpyxl,
            their transitive dependencies, plus setuptools/wheel to build
            the local project from source), as plain downloadable files.
  src/      A full copy of the PVT Lab Platform source tree (git archive
            of the exact commit this bundle was built from).

Requirements on the target PC: a plain Python 3.12+ install. No admin
rights are needed anywhere below -- everything happens inside a per-user
virtual environment. Streamlit here is an ordinary Python library
installed into that venv from wheels/, not a system service: it needs no
admin rights and runs no background server beyond the one 'streamlit run'
starts in your own user session while you're using it.

1. Copy/unzip this whole folder onto the target PC (e.g. from a USB stick).

2. Open a terminal INSIDE this folder and create a virtual environment:

     python -m venv .venv

3. Activate it:

     Windows (cmd.exe or PowerShell):
       .venv\\Scripts\\activate

     macOS / Linux (bash/zsh):
       source .venv/bin/activate

4. Install the build tools, then the project itself, entirely from the
   bundled wheels. --no-build-isolation stops pip from trying to fetch
   build-time dependencies on its own; setuptools/wheel are pre-installed
   into the venv in the first command below so that flag is safe to use:

     pip install --no-index --find-links wheels setuptools wheel
     cd src
     pip install --no-index --no-build-isolation --find-links ../wheels -e .

5. Run the web app (from inside src/, venv still active):

     streamlit run app.py

   (equivalently, from the bundle root instead of src/: streamlit run src/app.py)

6. CLI alternative -- same engine, no browser (from inside src/):

     python cli.py recombine --gor 850 --p_sep 815 --t_sep 145 --z_sep 0.855 --v_live 300 --p_recomb 5014.7 --t_recomb 200 --z_recomb 0.820
     python cli.py flash --workbook path\\to\\ADRIC_Flash_Separation_Calc_v6.1.xlsx
     python cli.py --help

Notes:
  - Every install command above uses --no-index, so pip fails loudly
    (rather than silently reaching the internet) if a required file is
    missing from wheels/. If that happens, this bundle was built for the
    wrong target platform -- rebuild it with the correct platform tag,
    e.g.: bash scripts/make_offline_bundle.sh win_amd64
  - The CLI (cli.py) only needs the pvt package plus openpyxl. The GUI
    (streamlit run app.py) additionally needs the streamlit package.
    Both are already included in wheels/.
EOF

# ── Report bundle path and size ───────────────────────────────────────────
if command -v du >/dev/null 2>&1; then
    BUNDLE_SIZE="$(du -sh "$BUNDLE_DIR" 2>/dev/null | cut -f1)"
else
    BUNDLE_SIZE="unknown"
fi

echo "make_offline_bundle.sh: wrote $BUNDLE_DIR ($BUNDLE_SIZE)"
