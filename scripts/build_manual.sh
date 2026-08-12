#!/usr/bin/env bash
# scripts/build_manual.sh — Build the ADRIC PVT Lab Platform software
# manual PDF from docs/manual/*.md via Pandoc.
#
# Concatenates docs/manual/00-title.md followed by chapters 01 through 11
# (docs/manual/01-*.md ... docs/manual/11-*.md, in numeric order) into
# docs/manual/PVT-Platform-Manual.pdf. Chapter discovery is shared with
# scripts/manual_to_tex.sh (CI's docs-smoke check) via
# scripts/manual_chapters.sh -- see that file for the contract.
#
# Requires: pandoc, and a LaTeX distribution providing pdflatex/xelatex
# (e.g. TeX Live / MacTeX / MiKTeX) on PATH.
#
# Fonts default to this project's usual macOS/MacTeX authoring machine
# (Times New Roman / Menlo) but can be overridden -- e.g. in CI, where
# those fonts don't exist -- via env vars:
#   PVT_MANUAL_MAINFONT   default: "Times New Roman"
#   PVT_MANUAL_MONOFONT   default: "Menlo"
#
# Usage:
#   bash scripts/build_manual.sh
#   PVT_MANUAL_MAINFONT="TeX Gyre Termes" PVT_MANUAL_MONOFONT="DejaVu Sans Mono" \
#       bash scripts/build_manual.sh

set -euo pipefail
shopt -s nullglob

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_PDF="$REPO_ROOT/docs/manual/PVT-Platform-Manual.pdf"

MAINFONT="${PVT_MANUAL_MAINFONT:-Times New Roman}"
MONOFONT="${PVT_MANUAL_MONOFONT:-Menlo}"

fail() {
    echo "build_manual.sh: ERROR: $*" >&2
    exit 1
}

# ── Tooling checks ───────────────────────────────────────────────────────
command -v pandoc >/dev/null 2>&1 \
    || fail "pandoc is not on PATH. Install pandoc to build the manual."
command -v pdflatex >/dev/null 2>&1 \
    || fail "pdflatex is not on PATH. Install a LaTeX distribution (e.g. TeX Live / MacTeX) to build the manual."

# ── Chapter checks (shared with scripts/manual_to_tex.sh) ───────────────
# shellcheck source=scripts/manual_chapters.sh
source "$SCRIPT_DIR/manual_chapters.sh"

# ── Figure checks ────────────────────────────────────────────────────────
# Chapters reference these figures via relative paths (figures/*.png),
# resolved through pandoc's --resource-path below. Fail loudly if any are
# missing rather than let pandoc silently emit a chapter with a broken image.
FIGURES_DIR="$MANUAL_DIR/figures"
REQUIRED_FIGURES=(flash-apparatus recombination-scheme app-workflow screen-map)
for fig in "${REQUIRED_FIGURES[@]}"; do
    [ -f "$FIGURES_DIR/$fig.png" ] \
        || fail "required figure missing: $FIGURES_DIR/$fig.png"
done

# ── Version metadata ─────────────────────────────────────────────────────
VERSION="$(cd "$REPO_ROOT" && git describe --tags --always 2>/dev/null || echo "unknown")"

echo "build_manual.sh: building manual (version: $VERSION)"
echo "build_manual.sh: fonts: mainfont=\"$MAINFONT\" monofont=\"$MONOFONT\""
echo "build_manual.sh: title page: ${TITLE_FILE#"$REPO_ROOT"/}"
for chapter in "${CHAPTERS[@]}"; do
    echo "build_manual.sh: chapter: ${chapter#"$REPO_ROOT"/}"
done

# ── Build ─────────────────────────────────────────────────────────────────
pandoc "$TITLE_FILE" "${CHAPTERS[@]}" \
    -o "$OUT_PDF" \
    --resource-path="$MANUAL_DIR" \
    --toc --toc-depth=2 \
    -V geometry:margin=2.5cm \
    -V documentclass=report \
    --pdf-engine=xelatex -V mainfont="$MAINFONT" -V monofont="$MONOFONT" \
    -H "$MANUAL_DIR/pdf-header.tex" \
    --metadata title="ADRIC PVT Lab Platform, Software Manual" \
    --metadata author="ADRIC / PVT Engineering" \
    --metadata date="$VERSION"

echo "build_manual.sh: wrote ${OUT_PDF#"$REPO_ROOT"/}"
