"""Independent recomputation of the synthetic workbook and test_cases.md.

Reads stored inputs on Actuals and Inputs-Drivers, rolls the same identities
the model uses, and compares the 12 expected values in test_cases.md. It does
not import those expected totals from the model package's check list.

A completed workbook is expected to contain formulas. A template workbook is
expected to leave Forecast, Budget-vs-Actual, and Summary empty.
"""

from __future__ import annotations

import re
import sys
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook

from fpa_driver_model.money import COGS_RATE, decimal_from_number, fmt_int, fmt_money, money
from fpa_driver_model.paths import test_cases_path, workbook_path

DEPTS = ["Engineering", "Sales", "Customer Success", "G&A"]

ACTUALS_ROWS = {
    "beginning": 7,
    "new": 8,
    "churned": 9,
    "ending": 10,
    "average": 11,
    "arpa": 12,
    "revenue": 13,
    "cogs": 14,
    "gross_profit": 15,
    "hc_Engineering": 16,
    "hc_Sales": 17,
    "hc_Customer Success": 18,
    "hc_G&A": 19,
    "total_hc": 20,
    "cph_Engineering": 21,
    "cph_Sales": 22,
    "cph_Customer Success": 23,
    "cph_G&A": 24,
    "people_cost": 25,
    "other_opex": 26,
    "total_opex": 27,
    "operating_income": 28,
}
DRIVER_FORECAST_ROWS = {
    "new": 14,
    "churned": 15,
    "arpa": 16,
    "hc_Engineering": 17,
    "hc_Sales": 18,
    "hc_Customer Success": 19,
    "hc_G&A": 20,
    "cph_Engineering": 21,
    "cph_Sales": 22,
    "cph_Customer Success": 23,
    "cph_G&A": 24,
    "other_opex": 25,
}
BUDGET_ROWS = {
    "new": 29,
    "churned": 30,
    "arpa": 31,
    "hc_Engineering": 32,
    "hc_Sales": 33,
    "hc_Customer Success": 34,
    "hc_G&A": 35,
    "cph_Engineering": 36,
    "cph_Sales": 37,
    "cph_Customer Success": 38,
    "cph_G&A": 39,
    "other_opex": 40,
    "beginning": 41,
    "ending": 42,
    "average": 43,
    "revenue": 44,
    "cogs": 45,
    "gross_profit": 46,
    "people_cost": 47,
    "total_opex": 48,
    "operating_income": 49,
}


def _cell_money(value: object) -> Decimal:
    return money(decimal_from_number(value))


def _month_from_inputs(
    beginning: int,
    new: int,
    churned: int,
    arpa: Decimal,
    headcount: dict[str, int],
    cost_per_head: dict[str, Decimal],
    other_opex: Decimal,
) -> dict[str, object]:
    ending = beginning + new - churned
    average = (Decimal(beginning) + Decimal(ending)) / Decimal(2)
    revenue = money(average * arpa)
    cogs = money(revenue * COGS_RATE)
    gross_profit = money(revenue - cogs)
    people_cost = money(sum(Decimal(headcount[dept]) * cost_per_head[dept] for dept in DEPTS))
    total_opex = money(people_cost + other_opex)
    return {
        "beginning": beginning,
        "new": new,
        "churned": churned,
        "ending": ending,
        "average": average,
        "arpa": money(arpa),
        "revenue": revenue,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "headcount": headcount,
        "total_hc": sum(headcount.values()),
        "cost_per_head": {dept: money(cost_per_head[dept]) for dept in DEPTS},
        "people_cost": people_cost,
        "other_opex": money(other_opex),
        "total_opex": total_opex,
        "operating_income": money(gross_profit - total_opex),
    }


def _read_month_block(worksheet: object, rows: dict[str, int], col: int) -> dict[str, object]:
    def ival(key: str) -> int:
        return int(worksheet.cell(rows[key], col).value)  # type: ignore[attr-defined]

    def dval(key: str) -> Decimal:
        return _cell_money(worksheet.cell(rows[key], col).value)  # type: ignore[attr-defined]

    return {
        "beginning": ival("beginning") if "beginning" in rows else None,
        "new": ival("new"),
        "churned": ival("churned"),
        "ending": ival("ending") if "ending" in rows else None,
        "arpa": dval("arpa"),
        "headcount": {dept: ival(f"hc_{dept}") for dept in DEPTS},
        "cost_per_head": {dept: dval(f"cph_{dept}") for dept in DEPTS},
        "other_opex": dval("other_opex"),
        "raw": {key: worksheet.cell(row, col).value for key, row in rows.items()},  # type: ignore[attr-defined]
    }


def _check_series(
    label: str, stored: list[dict[str, object]], opening: int
) -> list[dict[str, object]]:
    recomputed: list[dict[str, object]] = []
    beginning = opening
    for index, month in enumerate(stored):
        rec = _month_from_inputs(
            beginning,
            int(month["new"]),  # type: ignore[arg-type]
            int(month["churned"]),  # type: ignore[arg-type]
            month["arpa"],  # type: ignore[arg-type]
            month["headcount"],  # type: ignore[arg-type]
            month["cost_per_head"],  # type: ignore[arg-type]
            month["other_opex"],  # type: ignore[arg-type]
        )
        if month["beginning"] is not None and month["beginning"] != beginning:
            raise AssertionError(
                f"{label} month {index + 1} beginning {month['beginning']} != {beginning}"
            )
        if month["ending"] is not None and month["ending"] != rec["ending"]:
            raise AssertionError(
                f"{label} month {index + 1} ending {month['ending']} != {rec['ending']}"
            )
        raw = month["raw"]
        if isinstance(raw, dict):
            for key in (
                "average",
                "revenue",
                "cogs",
                "gross_profit",
                "people_cost",
                "total_opex",
                "operating_income",
            ):
                if key in raw and raw[key] is not None:
                    got = (
                        decimal_from_number(raw[key]) if key == "average" else _cell_money(raw[key])
                    )
                    if got != rec[key]:
                        raise AssertionError(
                            f"{label} month {index + 1} {key}: workbook {got} != recomputed {rec[key]}"
                        )
            if "total_hc" in raw and int(raw["total_hc"]) != rec["total_hc"]:
                raise AssertionError(f"{label} month {index + 1} total HC mismatch")
        beginning = int(rec["ending"])  # type: ignore[arg-type]
        recomputed.append(rec)
    return recomputed


def _parse_test_cases(path: Path) -> dict[int, str]:
    found: dict[int, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\| (\d+) \| .* \| ([^|]+) \|\s*$", line)
        if match:
            found[int(match.group(1))] = match.group(2).strip()
    if set(found) != set(range(1, 13)):
        raise AssertionError(f"Expected tests 1–12 in {path.name}, found {sorted(found)}")
    return found


def _assert_empty(
    worksheet: object, rows: range, cols: range | list[int], label: str, errors: list[str]
) -> None:
    filled: list[str] = []
    for row in rows:
        for col in cols:
            value = worksheet.cell(row, col).value  # type: ignore[attr-defined]
            if value not in (None, ""):
                filled.append(f"{worksheet.title}!{worksheet.cell(row, col).coordinate}={value}")  # type: ignore[attr-defined]
    if filled:
        errors.append(f"{label} should be empty: " + ", ".join(filled[:8]))


def verify(workbook: Path, cases: Path) -> list[str]:
    """Return a list of problems. An empty list means the workbook ties out."""
    errors: list[str] = []
    if not workbook.is_file():
        return [f"workbook not found: {workbook}"]
    if not cases.is_file():
        return [f"test cases not found: {cases}"]
    try:
        return _verify_open(workbook, cases)
    except (AssertionError, TypeError, ValueError, KeyError) as exc:
        errors.append(str(exc))
        return errors


def _verify_open(workbook: Path, cases: Path) -> list[str]:
    errors: list[str] = []
    book = load_workbook(workbook, data_only=False)
    expected_sheets = ["Inputs-Drivers", "Actuals", "Forecast", "Budget-vs-Actual", "Summary"]
    if book.sheetnames != expected_sheets:
        errors.append(f"Unexpected sheets: {book.sheetnames}")

    formula_cells: list[str] = []
    for worksheet in book.worksheets:
        banner = str(worksheet["A1"].value or "")
        if not banner.startswith("SYNTHETIC DATA"):
            errors.append(f"{worksheet.title} A1 is missing the SYNTHETIC DATA banner")
        for row in worksheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    formula_cells.append(f"{worksheet.title}!{cell.coordinate}")
    completed = bool(formula_cells)
    if not completed:
        _assert_empty(book["Forecast"], range(7, 29), range(2, 15), "Forecast values", errors)
        _assert_empty(
            book["Budget-vs-Actual"], range(8, 18), range(2, 6), "BvA annual values", errors
        )
        _assert_empty(
            book["Budget-vs-Actual"], range(21, 33), range(2, 10), "BvA monthly values", errors
        )
        _assert_empty(book["Summary"], range(7, 21), range(2, 9), "Summary values", errors)
    _assert_empty(book["Actuals"], range(7, 29), [14], "Actuals FY Total column", errors)

    actuals_ws = book["Actuals"]
    stored_actuals = [_read_month_block(actuals_ws, ACTUALS_ROWS, col) for col in range(2, 14)]
    rec_actuals = _check_series("Actuals", stored_actuals, opening=90)

    drivers = book["Inputs-Drivers"]
    if int(drivers["B8"].value) != 90:
        errors.append(f"Drivers opening 2025 is {drivers['B8'].value}, expected 90")
    if int(drivers["B9"].value) != rec_actuals[-1]["ending"]:
        errors.append(
            f"Drivers 2026 opening {drivers['B9'].value} != Dec 2025 ending {rec_actuals[-1]['ending']}"
        )
    if _cell_money(drivers["B10"].value) != money(COGS_RATE):
        errors.append(f"COGS rate on Drivers is {drivers['B10'].value}")

    stored_budget = [_read_month_block(drivers, BUDGET_ROWS, col) for col in range(2, 14)]
    rec_budget = _check_series("Budget", stored_budget, opening=90)
    stored_forecast = [
        _read_month_block(drivers, DRIVER_FORECAST_ROWS, col) for col in range(2, 14)
    ]
    rec_forecast = _check_series(
        "Forecast-drivers", stored_forecast, opening=int(rec_actuals[-1]["ending"])
    )

    expected = {
        1: fmt_int(int(rec_actuals[0]["ending"])),  # type: ignore[arg-type]
        2: fmt_money(rec_actuals[0]["revenue"]),  # type: ignore[arg-type]
        3: fmt_int(int(rec_actuals[-1]["ending"])),  # type: ignore[arg-type]
        4: fmt_money(money(sum(row["revenue"] for row in rec_actuals))),  # type: ignore[arg-type]
        5: fmt_money(money(sum(row["total_opex"] for row in rec_actuals))),  # type: ignore[arg-type]
        6: fmt_money(rec_actuals[0]["people_cost"]),  # type: ignore[arg-type]
        7: fmt_money(
            money(
                sum(row["revenue"] for row in rec_actuals)
                - sum(row["revenue"] for row in rec_budget)
            )  # type: ignore[arg-type]
        ),
        8: fmt_money(money(rec_actuals[11]["revenue"] - rec_budget[11]["revenue"])),  # type: ignore[operator]
        9: fmt_int(int(rec_forecast[0]["ending"])),  # type: ignore[arg-type]
        10: fmt_money(rec_forecast[0]["revenue"]),  # type: ignore[arg-type]
        11: fmt_int(int(rec_forecast[-1]["ending"])),  # type: ignore[arg-type]
        12: fmt_money(money(sum(row["total_opex"] for row in rec_forecast))),  # type: ignore[arg-type]
    }
    if rec_actuals[0]["revenue"] != money("184000.00"):
        errors.append("Hand check failed: Jan 2025 revenue")
    if rec_forecast[0]["revenue"] != money("335500.00"):
        errors.append("Hand check failed: Jan 2026 revenue")
    if rec_actuals[0]["people_cost"] != money("95500.00"):
        errors.append("Hand check failed: Jan 2025 people cost")
    if rec_forecast[0]["people_cost"] != money("134930.00"):
        errors.append("Hand check failed: Jan 2026 people cost")

    documented = _parse_test_cases(cases)
    for number in range(1, 13):
        if documented[number] != expected[number]:
            errors.append(
                f"test_cases.md #{number} is {documented[number]!r}, recomputed {expected[number]!r}"
            )

    if errors:
        return errors
    kind = "completed" if completed else "template"
    return [f"OK {kind} {workbook}"]


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in {"-h", "--help"}:
        print(
            "Usage: fpa-model verify [workbook.xlsx]\n"
            "Recomputes the synthetic workbook from its input tabs and checks test_cases.md.\n"
            "Does not write a workbook and does not call a model API."
        )
        return 0
    workbook = Path(args[0]) if args else workbook_path()
    outcome = verify(workbook, test_cases_path())
    if len(outcome) == 1 and outcome[0].startswith("OK "):
        completed = outcome[0].startswith("OK completed")
        print("VERIFICATION PASSED")
        print(f"Checked {'completed' if completed else 'template'} workbook: {workbook}")
        if completed:
            print(
                "Workbook opens, every tab has a SYNTHETIC DATA banner, and formulas are present."
            )
        else:
            print(
                "Workbook opens, every tab has a SYNTHETIC DATA banner, and no formulas are pre-built."
            )
        print("Actuals, the 2025 budget, and the 2026 driver rollforward all reconcile.")
        print("test_cases.md expected values match the independent recomputation.")
        return 0
    print("VERIFICATION FAILED")
    for item in outcome:
        print("-", item)
    return 1


if __name__ == "__main__":
    sys.exit(main())
