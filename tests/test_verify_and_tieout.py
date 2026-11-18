"""Workbook verifier, formula tie-out, chart, and a secret-shaped string scan."""

from __future__ import annotations

from pathlib import Path

from fpa_driver_model.chart import render_chart
from fpa_driver_model.cli import main
from fpa_driver_model.commentary import draft_commentary
from fpa_driver_model.paths import repo_root, workbook_path
from fpa_driver_model.synthetic import load_model
from fpa_driver_model.tieout import evaluate_workbook
from fpa_driver_model.verify_workbook import verify

FORMULA_CELLS = 481


def test_verifier_passes_on_the_built_workbook() -> None:
    assert main(["verify"]) == 0


def test_verifier_fails_when_a_check_is_changed(tmp_path: Path) -> None:
    cases = tmp_path / "test_cases.md"
    original = (repo_root() / "data" / "synthetic" / "test_cases.md").read_text(encoding="utf-8")
    cases.write_text(original.replace("$184,000.00", "$1.00", 1), encoding="utf-8")
    problems = verify(workbook_path(), cases)
    assert problems
    assert not any(item.startswith("OK ") for item in problems)


def test_every_formula_evaluates_and_matches_the_model() -> None:
    evaluated = evaluate_workbook(workbook_path())
    assert len(evaluated) == FORMULA_CELLS
    assert main(["verify"]) == 0
    assert load_model().forecast[0].revenue


def test_chart_is_a_png_from_the_model(tmp_path: Path) -> None:
    destination = render_chart(load_model(), tmp_path / "bridge.png")
    payload = destination.read_bytes()
    assert payload.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(payload) > 10_000


def test_checked_in_chart_is_a_png() -> None:
    payload = (repo_root() / "docs" / "fy2025-revenue-bridge.png").read_bytes()
    assert payload.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(payload) > 10_000


def test_checked_in_draft_matches_the_writer() -> None:
    draft = repo_root() / "examples" / "draft-commentary.md"
    assert draft.read_text(encoding="utf-8") == draft_commentary(load_model())


def test_repository_has_no_secret_shaped_text() -> None:
    banned = (
        "robinhood",
        "brokerage",
        "sk-ant-",
        "akia",
        "begin openssh",
        "begin rsa private",
        "ghp_",
        "xoxb-",
        "xoxp-",
        "api_key",
        "openai_api",
        "anthropic_api",
    )
    root = repo_root()
    offenders: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.suffix in {".png", ".xlsx", ".pyc"}:
            continue
        if path.name == "test_verify_and_tieout.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for needle in banned:
            if needle in text:
                offenders.append(f"{path.relative_to(root)} contains {needle}")
    assert offenders == []
