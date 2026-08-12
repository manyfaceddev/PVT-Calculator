#!/usr/bin/env bash
# scripts/manual_chapters.sh — shared chapter-discovery logic for the ADRIC
# PVT Lab Platform software manual.
#
# Sourced (not executed) by both scripts/build_manual.sh (full PDF build)
# and scripts/manual_to_tex.sh (CI docs-smoke: markdown -> .tex, no PDF
# engine), so the two ways of assembling the manual can never disagree
# about which chapters exist or what order they go in.
#
# Contract with the caller:
#   - REPO_ROOT must already be set (absolute path to the repo root).
#   - A `fail() { ... }` function must already be defined (both callers
#     define one that prints to stderr and exits non-zero).
#   - `shopt -s nullglob` must already be in effect (both callers set it
#     before sourcing this file) so an unmatched glob below expands to
#     nothing rather than the literal pattern.
#
# On success this file sets/populates, in the caller's shell:
#   MANUAL_DIR    docs/manual
#   TITLE_FILE    docs/manual/00-title.md
#   CHAPTERS      array of docs/manual/<NN>-*.md, chapters 01..11 in order
#
# Chapters 01-11 must each resolve to exactly one docs/manual/<NN>-*.md
# file, in that numeric order. Fails loudly (rather than silently building
# a partial manual) if a chapter is missing or a number is ambiguous.

MANUAL_DIR="$REPO_ROOT/docs/manual"
TITLE_FILE="$MANUAL_DIR/00-title.md"

[ -d "$MANUAL_DIR" ] || fail "manual directory not found: $MANUAL_DIR"
[ -f "$TITLE_FILE" ] || fail "title/abstract page missing: $TITLE_FILE"

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
