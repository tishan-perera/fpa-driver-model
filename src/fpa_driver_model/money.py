"""Cent rounding shared by the model, the verifier, and the workbook tie-out."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

CENTS = Decimal("0.01")
COGS_RATE = Decimal("0.20")


def money(value: Decimal | int | str) -> Decimal:
    """Round half-up to the cent, matching the workbook's currency convention."""
    amount = value if isinstance(value, Decimal) else Decimal(str(value))
    return amount.quantize(CENTS, rounding=ROUND_HALF_UP)


def decimal_from_number(value: object) -> Decimal:
    """Convert a workbook number without passing a binary float through money()."""
    if isinstance(value, bool) or value is None:
        raise TypeError(f"expected a number, got {value!r}")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, str):
        return Decimal(value)
    raise TypeError(f"expected a number, got {type(value).__name__}")


def fmt_money(value: Decimal) -> str:
    return f"${value:,.2f}"


def fmt_int(value: int) -> str:
    return f"{int(value):,}"


def fmt_quantity(value: Decimal) -> str:
    """Format a customer average that may be a whole number or a half."""
    if value == value.to_integral_value():
        return str(int(value))
    return format(value, "f")
