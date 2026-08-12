#!/usr/bin/env bash
# scripts/manual_to_tex.sh — CI docs-smoke helper: convert the manual's
# title page + chapters to LaTeX source (.tex) via pandoc only, WITHOUT
# invoking a PDF engine.
#
# This proves the chapter set is complete, correctly ordered, and
# pandoc-parseable (catches a missing/renamed/malformed chapter file,
# broken pandoc markdown, etc.) without needing a multi-hundred-MB LaTeX
# install in ordinary CI. The real PDF (via xelatex) is built by
# scripts/build_manual.sh, run in the release workflow where a full TeX
# Live install is already paid for.
#
# Reuses the same chapter discovery as scripts/build_manual.sh (see
# scripts/manual_chapters.sh) and the same non-PDF-engine pandoc flags
# (TOC, geometry, documentclass, typography header), just writing to a
# .tex file instead of a .pdf one.
#
# Requires: pandoc only (no pdflatex/xelatex, no LaTeX distribution).
#
# Usage:
#   bash scripts/manual_to_tex.sh [OUT_TEX]
#   Defaults to dist/manual-smoke/PVT-Platform-Manual.tex (gitignored via
#   the existing dist/ entry -- this is a throwaway smoke-test artifact,
#   never committed).

set -euo pipefail
shopt -s nullglob

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_TEX="${1:-$REPO_ROOT/dist/manual-smoke/PVT-Platform-Manual.tex}"

fail() {
    echo "manual_to_tex.sh: ERROR: $*" >&2
    exit 1
}

# ── Tooling checks ───────────────────────────────────────────────────────
command -v pandoc >/dev/null 2>&1 \
    || fail "pandoc is not on PATH. Install pandoc to run this check."

# ── Chapter checks (shared with scripts/build_manual.sh) ────────────────
# shellcheck source=scripts/manual_chapters.sh
source "$SCRIPT_DIR/manual_chapters.sh"

mkdir -p "$(dirname "$OUT_TEX")"

echo "manual_to_tex.sh: converting manual to LaTeX source (no PDF engine)"
echo "manual_to_tex.sh: title page: ${TITLE_FILE#"$REPO_ROOT"/}"
for chapter in "${CHAPTERS[@]}"; do
    echo "manual_to_tex.sh: chapter: ${chapter#"$REPO_ROOT"/}"
done

# ── Convert ───────────────────────────────────────────────────────────────
# Same document-shaping flags as build_manual.sh's pandoc call, minus
# --pdf-engine/-V mainfont/-V monofont (meaningless without a PDF engine
# actually compiling the output).
pandoc "$TITLE_FILE" "${CHAPTERS[@]}" \
    -o "$OUT_TEX" \
    --resource-path="$MANUAL_DIR" \
    --toc --toc-depth=2 \
    -V geometry:margin=2.5cm \
    -V documentclass=report \
    -H "$MANUAL_DIR/pdf-header.tex" \
    --metadata title="ADRIC PVT Lab Platform, Software Manual" \
    --metadata author="ADRIC / PVT Engineering" \
    --metadata date="ci-docs-smoke"

echo "manual_to_tex.sh: wrote ${OUT_TEX#"$REPO_ROOT"/}"
