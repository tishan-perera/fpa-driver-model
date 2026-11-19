"""Local variance draft. Off unless a caller asks for it. No network calls."""

from __future__ import annotations

from decimal import Decimal

from fpa_driver_model.money import fmt_int, fmt_money
from fpa_driver_model.synthetic import CompanyModel
from fpa_driver_model.variance import arr, revenue_bridge, signed_variance, sum_count, sum_money


def _call(amount: Decimal) -> str:
    if amount > 0:
        return "favorable"
    if amount < 0:
        return "unfavorable"
    return "zero"


def _cost_call(amount: Decimal) -> str:
    """A positive cost variance (actual above budget) is unfavorable."""
    if amount > 0:
        return "unfavorable"
    if amount < 0:
        return "favorable"
    return "zero"


def draft_commentary(model: CompanyModel) -> str:
    """Assemble a draft from the computed bridge. The result is not an approval."""
    bridge = revenue_bridge(model)
    actual_revenue = sum_money(model.actuals, "revenue")
    budget_revenue = sum_money(model.budget, "revenue")
    revenue_variance = signed_variance(actual_revenue, budget_revenue)
    actual_opex = sum_money(model.actuals, "total_opex")
    budget_opex = sum_money(model.budget, "total_opex")
    opex_variance = signed_variance(actual_opex, budget_opex)
    actual_people = sum_money(model.actuals, "people_cost")
    budget_people = sum_money(model.budget, "people_cost")
    people_variance = signed_variance(actual_people, budget_people)
    actual_other = sum_money(model.actuals, "other_opex")
    budget_other = sum_money(model.budget, "other_opex")
    other_variance = signed_variance(actual_other, budget_other)
    actual_gp = sum_money(model.actuals, "gross_profit")
    budget_gp = sum_money(model.budget, "gross_profit")
    gp_variance = signed_variance(actual_gp, budget_gp)
    actual_oi = sum_money(model.actuals, "operating_income")
    budget_oi = sum_money(model.budget, "operating_income")
    oi_variance = signed_variance(actual_oi, budget_oi)
    forecast_oi = sum_money(model.forecast, "operating_income")
    forecast_revenue = sum_money(model.forecast, "revenue")
    forecast_opex = sum_money(model.forecast, "total_opex")
    forecast_vs_actual_oi = signed_variance(forecast_oi, actual_oi)
    december_actual = model.actuals[-1]
    december_budget = model.budget[-1]
    december_forecast = model.forecast[-1]

    lines = [
        "# Variance commentary draft",
        "",
        "SYNTHETIC DATA — Fairhaven Metrics LLC is a fictional company. "
        "These figures are not a client, employer, or production forecast.",
        "",
        "Status: DRAFT. Not approved. An analyst has to approve this text before it is used.",
        "",
        "Sign convention: variance $ = actual − budget. A positive revenue or operating-income "
        "variance is favorable. A positive cost variance is unfavorable.",
        "",
        "## FY 2025 revenue",
        "",
        f"Actual revenue was {fmt_money(actual_revenue)}. "
        f"The original budget was {fmt_money(budget_revenue)}. "
        f"Variance (actual − budget) is {fmt_money(revenue_variance)} ({_call(revenue_variance)}).",
        "",
        f"Holding each month's ARPA at that month's budgeted ARPA, the volume piece is "
        f"{fmt_money(bridge.volume)} and the price piece is {fmt_money(bridge.price)}. "
        f"Those two pieces sum to the revenue variance of {fmt_money(bridge.variance)}.",
        "",
        "## Customers",
        "",
        f"December ending customers were {fmt_int(december_actual.ending)} versus the budget's "
        f"{fmt_int(december_budget.ending)}. "
        f"New customers were {fmt_int(sum_count(model.actuals, 'new'))} versus "
        f"{fmt_int(sum_count(model.budget, 'new'))}. "
        f"Churned customers were {fmt_int(sum_count(model.actuals, 'churned'))} versus "
        f"{fmt_int(sum_count(model.budget, 'churned'))}.",
        "",
        "## FY 2025 cost and operating income",
        "",
        f"Total opex was {fmt_money(actual_opex)} versus a budget of {fmt_money(budget_opex)}. "
        f"Variance (actual − budget) is {fmt_money(opex_variance)} ({_cost_call(opex_variance)}).",
        "",
        f"People cost was {fmt_money(actual_people)} versus {fmt_money(budget_people)} "
        f"(variance {fmt_money(people_variance)}). "
        f"Other opex was {fmt_money(actual_other)} versus {fmt_money(budget_other)} "
        f"(variance {fmt_money(other_variance)}).",
        "",
        f"Gross profit variance (actual − budget), after COGS, is {fmt_money(gp_variance)}. "
        f"Operating income was {fmt_money(actual_oi)} versus a budget of {fmt_money(budget_oi)}. "
        f"Variance (actual − budget) is {fmt_money(oi_variance)} ({_call(oi_variance)}).",
        "",
        "## 2026 forecast",
        "",
        f"The 2026 forecast, rolled from the monthly drivers, ends at "
        f"{fmt_int(december_forecast.ending)} customers. "
        f"December ARPA is {fmt_money(december_forecast.arpa)}. "
        f"December headcount is {fmt_int(december_forecast.total_hc)}. "
        f"December ARR is {fmt_money(arr(december_forecast))}. "
        f"FY forecast revenue is {fmt_money(forecast_revenue)}. "
        f"FY forecast total opex is {fmt_money(forecast_opex)}. "
        f"FY forecast operating income is {fmt_money(forecast_oi)}. "
        f"2025 actual operating income is {fmt_money(actual_oi)}. "
        f"Forecast minus 2025 actual operating income is {fmt_money(forecast_vs_actual_oi)}.",
        "",
        "This is a forecast from the drivers, for a fictional company.",
        "",
        "This draft was assembled locally from the model totals above. A hosted model was not called.",
        "",
        "Status: DRAFT",
        "",
    ]
    return "\n".join(lines)
