"""Model identities and the published synthetic checks."""

from __future__ import annotations

import itertools
from decimal import Decimal

from fpa_driver_model.checks import build_checks, render_test_cases
from fpa_driver_model.money import money
from fpa_driver_model.paths import test_cases_path as cases_file
from fpa_driver_model.synthetic import COST_2025, COST_2026, OPENING_2025, load_model
from fpa_driver_model.variance import revenue_bridge, signed_variance, sum_money


def test_customer_chain_and_opening_link() -> None:
    model = load_model()
    assert model.actuals[0].beginning == OPENING_2025
    assert model.budget[0].beginning == OPENING_2025
    assert model.forecast[0].beginning == model.actuals[-1].ending
    for series in (model.actuals, model.budget, model.forecast):
        for previous, month in itertools.pairwise(series):
            assert month.beginning == previous.ending
            assert month.ending == month.beginning + month.new - month.churned


def test_revenue_uses_average_customers() -> None:
    january = load_model().actuals[0]
    average = (Decimal(january.beginning) + Decimal(january.ending)) / Decimal(2)
    assert january.revenue == money(average * january.arpa)
    assert january.revenue == money("184000.00")


def test_published_hand_checks() -> None:
    model = load_model()
    assert model.forecast[0].revenue == money("335500.00")
    assert model.actuals[0].people_cost == money("95500.00")
    assert model.forecast[0].people_cost == money("134930.00")


def test_2026_rates_are_three_percent_above_2025() -> None:
    for before, after in zip(COST_2025, COST_2026, strict=True):
        assert after == money(before * Decimal("1.03"))


def test_revenue_bridge_sums_to_the_variance() -> None:
    model = load_model()
    bridge = revenue_bridge(model)
    assert money(bridge.volume + bridge.price) == bridge.variance
    assert bridge.variance == signed_variance(
        sum_money(model.actuals, "revenue"),
        sum_money(model.budget, "revenue"),
    )


def test_operating_income_walk() -> None:
    model = load_model()
    gross_profit = signed_variance(
        sum_money(model.actuals, "gross_profit"),
        sum_money(model.budget, "gross_profit"),
    )
    opex = signed_variance(
        sum_money(model.actuals, "total_opex"),
        sum_money(model.budget, "total_opex"),
    )
    income = signed_variance(
        sum_money(model.actuals, "operating_income"),
        sum_money(model.budget, "operating_income"),
    )
    assert money(gross_profit - opex) == income


def test_twelve_checks_are_internally_consistent() -> None:
    checks = build_checks(load_model())
    assert [check.number for check in checks] == list(range(1, 13))
    assert len({check.expected for check in checks}) == 12


def test_checked_in_test_cases_match_the_model() -> None:
    model = load_model()
    assert cases_file().read_text(encoding="utf-8") == render_test_cases(model)
