#!/usr/bin/env bash
# scripts/build_manual.sh — Build the ADRIC PVT Lab Platform software
# manual PDF from docs/manual/*.md via Pandoc.
#
# Concatenates docs/manual/00-title.md followed by chapters 01 through 11
# (docs/manual/01-*.md ... docs/manual/11-*.md, in numeric order) into
# docs/manual/PVT-Platform-Manual.pdf.
#
# Requires: pandoc, and a LaTeX distribution providing pdflatex
# (e.g. TeX Live / MacTeX / MiKTeX) on PATH.
#
# Usage:
#   bash scripts/build_manual.sh

set -euo pipefail
shopt -s nullglob

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MANUAL_DIR="$REPO_ROOT/docs/manual"
TITLE_FILE="$MANUAL_DIR/00-title.md"
OUT_PDF="$MANUAL_DIR/PVT-Platform-Manual.pdf"

fail() {
    echo "build_manual.sh: ERROR: $*" >&2
    exit 1
}

# ── Tooling checks ───────────────────────────────────────────────────────
command -v pandoc >/dev/null 2>&1 \
    || fail "pandoc is not on PATH. Install pandoc to build the manual."
command -v pdflatex >/dev/null 2>&1 \
    || fail "pdflatex is not on PATH. Install a LaTeX distribution (e.g. TeX Live / MacTeX) to build the manual."

# ── Chapter checks ───────────────────────────────────────────────────────
[ -d "$MANUAL_DIR" ] || fail "manual directory not found: $MANUAL_DIR"
[ -f "$TITLE_FILE" ] || fail "title/abstract page missing: $TITLE_FILE"

# Chapters 01-11 must each resolve to exactly one docs/manual/<NN>-*.md
# file, in that numeric order. Fail loudly (rather than silently building
# a partial manual) if a chapter is missing or a number is ambiguous.
CHAPTERS=()
for n in 01 02 03 04 05 06 07 08 09 10 11; do
    matches=("$MANUAL_DIR"/"$n"-*.md)
    if [ "${#matches[@]}" -eq 0 ]; then
        fail "chapter $n is missing: no file matching docs/manual/$n-*.md"
    fi
    if [ "${#matches[@]}" -gt 1 ]; then
        fail "chapter $n is ambiguous: multiple files match docs/manual/$n-*.md (${matches[*]})"
    fi
    CHAPTERS+=("${matches[0]}")
done

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
    --pdf-engine=xelatex -V mainfont="Times New Roman" -V monofont="Menlo" \
    -H "$MANUAL_DIR/pdf-header.tex" \
    --metadata title="ADRIC PVT Lab Platform, Software Manual" \
    --metadata author="ADRIC / PVT Engineering" \
    --metadata date="$VERSION"

echo "build_manual.sh: wrote ${OUT_PDF#"$REPO_ROOT"/}"
