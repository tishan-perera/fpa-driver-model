"""Locate the checkout that holds the synthetic workbook."""

from __future__ import annotations

from pathlib import Path

WORKBOOK_NAME = "Fairhaven_Metrics_FP&A_Model_SYNTHETIC_built.xlsx"


def repo_root() -> Path:
    """Return the repository root when this package is used from a checkout."""
    here = Path(__file__).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "data" / "synthetic").is_dir():
            return candidate
    raise FileNotFoundError(
        "Could not find the checkout (pyproject.toml and data/synthetic). "
        "Clone the repository and install it in editable mode."
    )


def synthetic_dir() -> Path:
    return repo_root() / "data" / "synthetic"


def workbook_path() -> Path:
    return synthetic_dir() / WORKBOOK_NAME


def test_cases_path() -> Path:
    return synthetic_dir() / "test_cases.md"
