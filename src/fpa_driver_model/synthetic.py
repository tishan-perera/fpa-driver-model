"""Fictional drivers and the roll-forward that turns them into a full year.

Fairhaven Metrics LLC is not a real company. The monthly inputs are the
synthetic dataset. Revenue, cost, and operating income are computed from
those inputs; they are not typed in as results.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fpa_driver_model.money import COGS_RATE, money

DEPTS: tuple[str, ...] = ("Engineering", "Sales", "Customer Success", "G&A")
MONTHS_2025: tuple[str, ...] = (
    "Jan 2025",
    "Feb 2025",
    "Mar 2025",
    "Apr 2025",
    "May 2025",
    "Jun 2025",
    "Jul 2025",
    "Aug 2025",
    "Sep 2025",
    "Oct 2025",
    "Nov 2025",
    "Dec 2025",
)
MONTHS_2026: tuple[str, ...] = (
    "Jan 2026",
    "Feb 2026",
    "Mar 2026",
    "Apr 2026",
    "May 2026",
    "Jun 2026",
    "Jul 2026",
    "Aug 2026",
    "Sep 2026",
    "Oct 2026",
    "Nov 2026",
    "Dec 2026",
)

OPENING_2025 = 90
HEADCOUNT = tuple[int, int, int, int]
Rates = tuple[Decimal, Decimal, Decimal, Decimal]

COST_2025: Rates = (
    money(10_000),
    money(8_500),
    money(7_000),
    money(8_000),
)
# 2026 cost per head is 3% above the 2025 rate, rounded half-up to the cent.
COST_2026: Rates = tuple(money(rate * Decimal("1.03")) for rate in COST_2025)


@dataclass(frozen=True)
class Month:
    label: str
    beginning: int
    new: int
    churned: int
    ending: int
    average: Decimal
    arpa: Decimal
    revenue: Decimal
    cogs: Decimal
    gross_profit: Decimal
    headcount: HEADCOUNT
    cost_per_head: Rates
    people_cost: Decimal
    other_opex: Decimal
    total_opex: Decimal
    operating_income: Decimal

    @property
    def total_hc(self) -> int:
        return sum(self.headcount)


@dataclass(frozen=True)
class CompanyModel:
    """One synthetic company: 2025 actuals, the 2025 budget, and the 2026 forecast."""

    actuals: tuple[Month, ...]
    budget: tuple[Month, ...]
    forecast: tuple[Month, ...]

    @property
    def opening_2026(self) -> int:
        return self.actuals[-1].ending


def _month(
    label: str,
    beginning: int,
    new: int,
    churned: int,
    arpa: Decimal,
    headcount: HEADCOUNT,
    cost_per_head: Rates,
    other_opex: Decimal,
) -> Month:
    ending = beginning + new - churned
    if ending < 0:
        raise ValueError(f"{label} would end with negative customers")
    average = (Decimal(beginning) + Decimal(ending)) / Decimal(2)
    revenue = money(average * arpa)
    cogs = money(revenue * COGS_RATE)
    gross_profit = money(revenue - cogs)
    people_cost = money(
        sum(
            (Decimal(heads) * rate for heads, rate in zip(headcount, cost_per_head, strict=True)),
            Decimal(0),
        )
    )
    other = money(other_opex)
    total_opex = money(people_cost + other)
    operating_income = money(gross_profit - total_opex)
    return Month(
        label=label,
        beginning=beginning,
        new=new,
        churned=churned,
        ending=ending,
        average=average,
        arpa=money(arpa),
        revenue=revenue,
        cogs=cogs,
        gross_profit=gross_profit,
        headcount=headcount,
        cost_per_head=tuple(money(rate) for rate in cost_per_head),
        people_cost=people_cost,
        other_opex=other,
        total_opex=total_opex,
        operating_income=operating_income,
    )


def _roll(
    labels: tuple[str, ...],
    opening: int,
    new: list[int],
    churned: list[int],
    arpa: list[Decimal],
    headcount: list[HEADCOUNT],
    cost_per_head: Rates,
    other_opex: list[Decimal],
) -> tuple[Month, ...]:
    rows: list[Month] = []
    beginning = opening
    for index, label in enumerate(labels):
        row = _month(
            label,
            beginning,
            new[index],
            churned[index],
            arpa[index],
            headcount[index],
            cost_per_head,
            other_opex[index],
        )
        rows.append(row)
        beginning = row.ending
    return tuple(rows)


def _repeat(row: HEADCOUNT, quarters: int) -> list[HEADCOUNT]:
    return [row] * (quarters * 3)


def load_model() -> CompanyModel:
    """Build the synthetic model from the monthly driver inputs."""
    actual_hc = (
        _repeat((4, 3, 2, 2), 1)
        + _repeat((5, 3, 2, 2), 1)
        + _repeat((5, 4, 3, 2), 1)
        + _repeat((6, 4, 3, 2), 1)
    )
    budget_hc = [(4, 3, 2, 2)] * 6 + [(5, 3, 3, 2)] * 6
    forecast_hc = (
        _repeat((6, 4, 3, 2), 1)
        + _repeat((6, 5, 3, 2), 1)
        + _repeat((7, 5, 4, 2), 1)
        + _repeat((7, 5, 4, 3), 1)
    )
    actuals = _roll(
        MONTHS_2025,
        OPENING_2025,
        [6, 7, 6, 8, 7, 8, 7, 8, 7, 9, 8, 8],
        [2, 2, 2, 2, 3, 2, 3, 2, 3, 3, 2, 3],
        [
            Decimal(v)
            for v in (2000, 2000, 2000, 2050, 2050, 2050, 2100, 2100, 2100, 2150, 2150, 2200)
        ],
        actual_hc,
        COST_2025,
        [
            money(v)
            for v in (5500, 5500, 5500, 5500, 5500, 5500, 6500, 6500, 6500, 6500, 6500, 6500)
        ],
    )
    budget = _roll(
        MONTHS_2025,
        OPENING_2025,
        [5, 6, 6, 6, 6, 7, 7, 7, 7, 7, 7, 7],
        [2, 2, 2, 2, 2, 2, 2, 2, 3, 2, 2, 2],
        [Decimal(2000)] * 12,
        budget_hc,
        COST_2025,
        [money(5000)] * 12,
    )
    forecast = _roll(
        MONTHS_2026,
        actuals[-1].ending,
        [8, 8, 9, 9, 9, 10, 9, 9, 10, 10, 9, 8],
        [3, 3, 3, 3, 4, 3, 4, 3, 4, 4, 3, 4],
        [
            Decimal(v)
            for v in (2200, 2200, 2200, 2250, 2250, 2250, 2250, 2300, 2300, 2300, 2300, 2300)
        ],
        forecast_hc,
        COST_2026,
        [
            money(v)
            for v in (7000, 7000, 7000, 7500, 7500, 7500, 8000, 8000, 8000, 8000, 7500, 7000)
        ],
    )
    model = CompanyModel(actuals=actuals, budget=budget, forecast=forecast)
    _assert_identities(model)
    return model


def _assert_identities(model: CompanyModel) -> None:
    """Fail closed if a roll-forward breaks the definitions the workbook uses."""
    if model.actuals[0].beginning != OPENING_2025 or model.budget[0].beginning != OPENING_2025:
        raise AssertionError("2025 must open at the synthetic opening balance")
    if model.forecast[0].beginning != model.actuals[-1].ending:
        raise AssertionError("January 2026 must open at December 2025 ending customers")
    for series in (model.actuals, model.budget, model.forecast):
        previous: Month | None = None
        for month in series:
            if previous is not None and month.beginning != previous.ending:
                raise AssertionError(f"{month.label} does not roll forward from the prior month")
            if month.ending != month.beginning + month.new - month.churned:
                raise AssertionError(f"{month.label} customer roll-forward is inconsistent")
            if month.revenue != money(month.average * month.arpa):
                raise AssertionError(f"{month.label} revenue is not average customers times ARPA")
            if month.cogs != money(month.revenue * COGS_RATE):
                raise AssertionError(f"{month.label} COGS is not revenue times the COGS rate")
            if month.gross_profit != money(month.revenue - month.cogs):
                raise AssertionError(f"{month.label} gross profit identity failed")
            if month.total_opex != money(month.people_cost + month.other_opex):
                raise AssertionError(f"{month.label} opex identity failed")
            if month.operating_income != money(month.gross_profit - month.total_opex):
                raise AssertionError(f"{month.label} operating income identity failed")
            previous = month
