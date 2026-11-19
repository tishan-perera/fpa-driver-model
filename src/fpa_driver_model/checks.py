"""The 12 published checks, rendered from the model rather than typed as results."""

from __future__ import annotations

from dataclasses import dataclass

from fpa_driver_model.money import fmt_int, fmt_money, fmt_quantity
from fpa_driver_model.synthetic import CompanyModel, Month
from fpa_driver_model.variance import revenue_bridge, signed_variance, sum_money


@dataclass(frozen=True)
class Check:
    number: int
    name: str
    how: str
    expected: str


def build_checks(model: CompanyModel) -> tuple[Check, ...]:
    actual_jan = model.actuals[0]
    forecast_jan = model.forecast[0]
    actual_revenue = sum_money(model.actuals, "revenue")
    budget_revenue = sum_money(model.budget, "revenue")
    actual_opex = sum_money(model.actuals, "total_opex")
    forecast_opex = sum_money(model.forecast, "total_opex")
    december_revenue_variance = signed_variance(model.actuals[-1].revenue, model.budget[-1].revenue)
    return (
        Check(
            1,
            "January 2025 ending customers",
            (
                f"Beginning {actual_jan.beginning} + new {actual_jan.new} "
                f"− churned {actual_jan.churned}."
            ),
            fmt_int(actual_jan.ending),
        ),
        Check(
            2,
            "January 2025 revenue",
            (
                f"Average customers = ({actual_jan.beginning} + {actual_jan.ending}) / 2 "
                f"= {fmt_quantity(actual_jan.average)}. "
                f"Revenue = {fmt_quantity(actual_jan.average)} × {fmt_money(actual_jan.arpa)} ARPA."
            ),
            fmt_money(actual_jan.revenue),
        ),
        Check(
            3,
            "December 2025 ending customers",
            "Roll the 2025 actuals customer chain through December. Also the opening balance for January 2026.",
            fmt_int(model.actuals[-1].ending),
        ),
        Check(
            4,
            "FY 2025 actual revenue",
            "Sum of monthly actual revenue for Jan–Dec 2025.",
            fmt_money(actual_revenue),
        ),
        Check(
            5,
            "FY 2025 actual total opex",
            "Sum of monthly actual total opex (people cost + other opex) for Jan–Dec 2025.",
            fmt_money(actual_opex),
        ),
        Check(
            6,
            "January 2025 people cost",
            _people_how(actual_jan),
            fmt_money(actual_jan.people_cost),
        ),
        Check(
            7,
            "FY 2025 revenue variance (Actual − Budget)",
            "FY 2025 actual revenue minus FY 2025 budget revenue.",
            fmt_money(signed_variance(actual_revenue, budget_revenue)),
        ),
        Check(
            8,
            "December 2025 revenue variance (Actual − Budget)",
            "December 2025 actual revenue minus December 2025 budget revenue.",
            fmt_money(december_revenue_variance),
        ),
        Check(
            9,
            "January 2026 forecast ending customers",
            (
                f"Beginning {forecast_jan.beginning} (Dec 2025 ending) + new {forecast_jan.new} "
                f"− churned {forecast_jan.churned}."
            ),
            fmt_int(forecast_jan.ending),
        ),
        Check(
            10,
            "January 2026 forecast revenue (forecast month 1)",
            (
                f"Average customers = ({forecast_jan.beginning} + {forecast_jan.ending}) / 2 "
                f"= {fmt_quantity(forecast_jan.average)}. "
                f"Revenue = {fmt_quantity(forecast_jan.average)} × {fmt_money(forecast_jan.arpa)} ARPA."
            ),
            fmt_money(forecast_jan.revenue),
        ),
        Check(
            11,
            "December 2026 forecast ending customers (forecast month 12)",
            "Roll the 2026 driver customer chain through December.",
            fmt_int(model.forecast[-1].ending),
        ),
        Check(
            12,
            "FY 2026 forecast total opex",
            (
                "Sum of monthly forecast total opex (people cost + other opex) for Jan–Dec 2026. "
                "Use 2026 cost-per-head rates."
            ),
            fmt_money(forecast_opex),
        ),
    )


def _people_how(month: Month) -> str:
    parts = [f"({month.headcount[i]} × {fmt_money(month.cost_per_head[i])})" for i in range(4)]
    return " + ".join(parts) + "."


def render_test_cases(model: CompanyModel) -> str:
    """Markdown the workbook verifier parses. Expected values come from the model."""
    bridge = revenue_bridge(model)
    checks = build_checks(model)
    lines = [
        "# Test cases — Fairhaven Metrics LLC FP&A model (SYNTHETIC)",
        "",
        "All expected values were computed by `fpa_driver_model` from the synthetic drivers,",
        "then checked again by `fpa-model verify` from the workbook inputs.",
        "",
        "## Conventions",
        "",
        "Customer rollforward: Ending customers = Beginning customers + New customers − Churned customers. "
        "Beginning customers in month 1 of a year equal ending customers of the prior month "
        "(January 2025 beginning is the 1 January 2025 opening balance; January 2026 beginning "
        "must equal December 2025 ending customers). "
        "Average customers = (Beginning + Ending) / 2. "
        "Revenue = Average customers × monthly ARPA (average revenue per account per month, USD). "
        "This model uses average customers, not ending customers, for revenue. "
        "COGS = Revenue × 20%. "
        "People cost = Engineering HC × Eng cost/head + Sales HC × Sales cost/head + "
        "CS HC × CS cost/head + G&A HC × G&A cost/head. "
        "Total opex = People cost + Other opex. "
        "Gross profit = Revenue − COGS. "
        "Operating income = Gross profit − Total opex. "
        "ARR = Ending customers × monthly ARPA × 12. "
        "Budget-vs-Actual variance $ = Actual − Budget (positive means favorable for revenue and "
        "operating income, and unfavorable for costs). "
        "Variance % = Variance $ / Budget, when Budget is not zero.",
        "",
        "Do not paste these expected values into the Forecast, Budget-vs-Actual, or Summary tabs. "
        "Those tabs should stay formula-driven.",
        "",
        "## Checks",
        "",
        "| # | Check | How it is computed | Expected value |",
        "| --- | --- | --- | ---: |",
    ]
    for check in checks:
        lines.append(f"| {check.number} | {check.name} | {check.how} | {check.expected} |")
    lines.extend(
        [
            "",
            "## Reference totals (not additional pass/fail checks)",
            "",
            "These are printed so a reviewer can see the annual picture. They come from the same model.",
            "",
            f"- FY 2025 budget revenue: {fmt_money(sum_money(model.budget, 'revenue'))}",
            f"- FY 2025 budget total opex: {fmt_money(sum_money(model.budget, 'total_opex'))}",
            f"- FY 2026 forecast revenue: {fmt_money(sum_money(model.forecast, 'revenue'))}",
            f"- FY 2026 forecast total opex: {fmt_money(sum_money(model.forecast, 'total_opex'))}",
            f"- FY 2025 revenue variance: {fmt_money(bridge.variance)}",
            "",
            "SYNTHETIC DATA — fictional company, not for production use.",
            "",
        ]
    )
    return "\n".join(lines)
