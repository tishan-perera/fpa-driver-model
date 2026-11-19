"""Commentary stays off until asked for, and approval is an explicit decision."""

from __future__ import annotations

from pathlib import Path

from fpa_driver_model.checks import build_checks
from fpa_driver_model.cli import main
from fpa_driver_model.commentary import draft_commentary
from fpa_driver_model.money import fmt_money
from fpa_driver_model.report import render_report
from fpa_driver_model.review import review_status
from fpa_driver_model.synthetic import load_model
from fpa_driver_model.variance import revenue_bridge


def test_default_report_does_not_draft_commentary() -> None:
    report = render_report(load_model(), commentary=None)
    assert "Nothing was drafted" in report
    assert "Status: DRAFT" not in report


def test_draft_uses_only_computed_money_and_stays_unapproved() -> None:
    model = load_model()
    draft = draft_commentary(model)
    assert "SYNTHETIC DATA" in draft
    assert "Status: DRAFT" in draft
    assert "Not approved" in draft
    assert "A hosted model was not called." in draft
    assert fmt_money(revenue_bridge(model).variance) in draft
    assert fmt_money(revenue_bridge(model).volume) in draft
    assert fmt_money(revenue_bridge(model).price) in draft
    for check in build_checks(model):
        if check.expected.startswith("$"):
            assert check.expected in draft or check.number in {1, 2, 3, 6, 8, 9, 10}


def test_opex_call_follows_the_sign_of_the_model() -> None:
    from fpa_driver_model.variance import signed_variance, sum_money

    model = load_model()
    variance = signed_variance(
        sum_money(model.actuals, "total_opex"), sum_money(model.budget, "total_opex")
    )
    draft = draft_commentary(model)
    if variance > 0:
        assert "unfavorable" in draft
    elif variance < 0:
        assert "favorable" in draft


def test_approval_is_pending_until_a_reviewer_decides(tmp_path: Path) -> None:
    draft = tmp_path / "draft.md"
    draft.write_text(draft_commentary(load_model()), encoding="utf-8")
    assert review_status(draft) == "pending"
    assert main(["status", str(draft)]) == 0
    assert (
        main(["approve", str(draft), "--reviewer", "A. Analyst", "--note", "Bridge ties out."]) == 0
    )
    assert review_status(draft) == "approved"
    draft.write_text(draft.read_text(encoding="utf-8") + "\nEdited.\n", encoding="utf-8")
    assert review_status(draft) == "stale"


def test_reject_and_blank_reviewer(tmp_path: Path, capsys: object) -> None:
    draft = tmp_path / "draft.md"
    draft.write_text(draft_commentary(load_model()), encoding="utf-8")
    assert (
        main(
            ["reject", str(draft), "--reviewer", "A. Analyst", "--note", "Needs a clearer bridge."]
        )
        == 0
    )
    assert review_status(draft) == "rejected"
    code = main(["approve", str(draft), "--reviewer", "   ", "--note", ""])
    assert code == 2
    del capsys


def test_commentary_module_does_not_reference_a_network_client() -> None:
    source = Path("src/fpa_driver_model/commentary.py").read_text(encoding="utf-8")
    for name in ("urllib", "requests", "httpx", "openai", "anthropic", "socket"):
        assert name not in source
