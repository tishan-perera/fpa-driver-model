"""Plain-text run report. Every figure is formatted from the model."""

from __future__ import annotations

from fpa_driver_model.checks import build_checks
from fpa_driver_model.money import fmt_int, fmt_money
from fpa_driver_model.synthetic import CompanyModel
from fpa_driver_model.variance import arr, revenue_bridge, signed_variance, sum_money


def _row(label: str, value: str) -> str:
    return f"  {label:<42} {value}"


def render_report(model: CompanyModel, *, commentary: str | None) -> str:
    bridge = revenue_bridge(model)
    actual_revenue = sum_money(model.actuals, "revenue")
    budget_revenue = sum_money(model.budget, "revenue")
    actual_opex = sum_money(model.actuals, "total_opex")
    budget_opex = sum_money(model.budget, "total_opex")
    actual_oi = sum_money(model.actuals, "operating_income")
    budget_oi = sum_money(model.budget, "operating_income")
    forecast_end = model.forecast[-1]
    lines = [
        "Fairhaven Metrics LLC — synthetic FP&A run",
        "SYNTHETIC DATA. Fictional company. Not a forecast for a live close.",
        "",
        "2026 forecast, rolled from the monthly drivers",
        _row("Opening customers (Dec 2025 ending)", fmt_int(model.opening_2026)),
        _row("December ending customers", fmt_int(forecast_end.ending)),
        _row("December monthly ARPA", fmt_money(forecast_end.arpa)),
        _row("December ARR", fmt_money(arr(forecast_end))),
        _row("December headcount", fmt_int(forecast_end.total_hc)),
        _row("FY revenue", fmt_money(sum_money(model.forecast, "revenue"))),
        _row("FY total opex", fmt_money(sum_money(model.forecast, "total_opex"))),
        _row("FY operating income", fmt_money(sum_money(model.forecast, "operating_income"))),
        "",
        "2025 actual versus original budget (actual − budget)",
        _row("Revenue actual", fmt_money(actual_revenue)),
        _row("Revenue budget", fmt_money(budget_revenue)),
        _row("Revenue variance", fmt_money(signed_variance(actual_revenue, budget_revenue))),
        _row("Volume piece (budget ARPA)", fmt_money(bridge.volume)),
        _row("Price piece", fmt_money(bridge.price)),
        _row("Total opex variance", fmt_money(signed_variance(actual_opex, budget_opex))),
        _row("Operating income variance", fmt_money(signed_variance(actual_oi, budget_oi))),
        "",
        "Published checks",
    ]
    for check in build_checks(model):
        lines.append(f"  {check.number:2d}. {check.expected:>16}  {check.name}")
    lines.extend(["", "Commentary"])
    if commentary is None:
        lines.append("  Off. Nothing was drafted and nothing was approved.")
        lines.append("  Draft with: fpa-model run --draft-commentary -o draft.md")
    else:
        lines.append("  A draft was assembled locally. It is not approved.")
        lines.append("  A hosted model was not called.")
    lines.append("")
    return "\n".join(lines)
