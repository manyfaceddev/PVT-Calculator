"""Absolute-path helper for AppTest script loading.

Streamlit >= 1.61 resolves AppTest.from_file() relative paths against the
CALLING test file (previously the working directory), which broke every
relative "ui/pages/..." reference in this suite. Resolving against the repo
root keeps the tests correct on every Streamlit version.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def repo_file(relative: str) -> str:
    """Absolute path to a repo file, for AppTest.from_file()."""
    return str(REPO_ROOT / relative)
