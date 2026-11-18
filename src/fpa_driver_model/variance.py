"""Budget-versus-actual variances and the revenue price/volume bridge."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fpa_driver_model.money import money
from fpa_driver_model.synthetic import CompanyModel, Month


def sum_money(months: tuple[Month, ...], name: str) -> Decimal:
    return money(sum((getattr(month, name) for month in months), Decimal(0)))


def sum_count(months: tuple[Month, ...], name: str) -> int:
    return int(sum(getattr(month, name) for month in months))


def arr(month: Month) -> Decimal:
    """December-style ARR: ending customers × that month's ARPA × 12."""
    return money(Decimal(month.ending) * month.arpa * Decimal(12))


@dataclass(frozen=True)
class RevenueBridge:
    budget_revenue: Decimal
    volume: Decimal
    price: Decimal
    actual_revenue: Decimal

    @property
    def variance(self) -> Decimal:
        return money(self.actual_revenue - self.budget_revenue)


def revenue_bridge(model: CompanyModel) -> RevenueBridge:
    """Split the revenue variance into volume (at budget ARPA) and price.

    Each month's volume piece holds ARPA at that month's budgeted ARPA and
    uses actual average customers. The price piece is what remains of the
    actual revenue. The two pieces sum to actual revenue minus budget revenue.
    """
    volume = Decimal(0)
    price = Decimal(0)
    for actual, budget in zip(model.actuals, model.budget, strict=True):
        held_at_budget_arpa = money(actual.average * budget.arpa)
        volume += held_at_budget_arpa - budget.revenue
        price += actual.revenue - held_at_budget_arpa
    return RevenueBridge(
        budget_revenue=sum_money(model.budget, "revenue"),
        volume=money(volume),
        price=money(price),
        actual_revenue=sum_money(model.actuals, "revenue"),
    )


def signed_variance(actual: Decimal, budget: Decimal) -> Decimal:
    """Actual minus budget. Positive is favorable for revenue and income, unfavorable for cost."""
    return money(actual - budget)
