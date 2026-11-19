"""Evaluate the Fairhaven workbook's formulas.

The grammar is the one this workbook uses: cell references, quoted and plain
sheet names, addition, subtraction, multiplication, division, parentheses,
and SUM of a rectangular range. It is not a general Excel engine.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string, get_column_letter
from openpyxl.workbook.workbook import Workbook

from fpa_driver_model.money import decimal_from_number, money
from fpa_driver_model.synthetic import CompanyModel
from fpa_driver_model.variance import arr, sum_count, sum_money


class FormulaError(ValueError):
    """A workbook formula is outside the grammar this tie-out evaluates."""


class _Parser:
    def __init__(self, formula: str, sheet: str, evaluator: WorkbookEvaluator) -> None:
        self.formula = formula
        self.source = formula[1:] if formula.startswith("=") else formula
        self.index = 0
        self.sheet = sheet
        self.evaluator = evaluator

    def parse(self) -> Decimal:
        value = self._expr()
        self._skip()
        if self.index != len(self.source):
            raise FormulaError(f"trailing input in {self.sheet}: {self.formula}")
        return value

    def _peek(self) -> str:
        return self.source[self.index] if self.index < len(self.source) else ""

    def _skip(self) -> None:
        while self._peek().isspace():
            self.index += 1

    def _expect(self, character: str) -> None:
        self._skip()
        if self._peek() != character:
            raise FormulaError(f"expected {character!r} in {self.formula}")
        self.index += 1

    def _expr(self) -> Decimal:
        self._skip()
        value = self._term()
        while True:
            self._skip()
            op = self._peek()
            if op not in {"+", "-"}:
                # A string membership test would treat "" as a match and invent an operator at end of input.
                return value
            self.index += 1
            right = self._term()
            value = value + right if op == "+" else value - right

    def _term(self) -> Decimal:
        self._skip()
        value = self._factor()
        while True:
            self._skip()
            op = self._peek()
            if op not in {"*", "/"}:
                return value
            self.index += 1
            right = self._factor()
            value = value * right if op == "*" else value / right

    def _factor(self) -> Decimal:
        self._skip()
        char = self._peek()
        if char == "(":
            self.index += 1
            value = self._expr()
            self._expect(")")
            return value
        if char.isdigit() or char == ".":
            return self._number()
        if char == "'":
            sheet, start, end = self._quoted_sheet_range()
            return (
                self.evaluator.sum_range(sheet, start, end)
                if end
                else self.evaluator.value(sheet, start)
            )
        if char == "$" or char.isalpha():
            return self._name_or_ref()
        raise FormulaError(f"cannot read {self.formula!r} on {self.sheet}")

    def _number(self) -> Decimal:
        start = self.index
        while self._peek().isdigit() or self._peek() == ".":
            self.index += 1
        return Decimal(self.source[start : self.index])

    def _letters(self) -> str:
        start = self.index
        while self._peek().isalpha():
            self.index += 1
        if start == self.index:
            raise FormulaError(f"expected a name in {self.formula}")
        return self.source[start : self.index]

    def _digits(self) -> str:
        start = self.index
        while self._peek().isdigit():
            self.index += 1
        if start == self.index:
            raise FormulaError(f"expected a row number in {self.formula}")
        return self.source[start : self.index]

    def _cell(self) -> str:
        self._skip()
        if self._peek() == "$":
            self.index += 1
        letters = self._letters()
        if self._peek() == "$":
            self.index += 1
        return f"{letters.upper()}{self._digits()}"

    def _quoted_sheet_range(self) -> tuple[str, str, str | None]:
        self._expect("'")
        start = self.index
        while self._peek() and self._peek() != "'":
            self.index += 1
        sheet = self.source[start : self.index]
        self._expect("'")
        self._expect("!")
        first = self._cell()
        if self._peek() == ":":
            self.index += 1
            return sheet, first, self._cell()
        return sheet, first, None

    def _name_or_ref(self) -> Decimal:
        if self._peek() == "$":
            return self.evaluator.value(self.sheet, self._cell())
        letters = self._letters()
        self._skip()
        if letters.lower() == "sum" and self._peek() == "(":
            self.index += 1
            sheet, start, end = self._sum_argument()
            self._expect(")")
            if end is None:
                raise FormulaError(f"SUM needs a range in {self.formula}")
            return self.evaluator.sum_range(sheet, start, end)
        if self._peek() == "!":
            self.index += 1
            first = self._cell()
            if self._peek() == ":":
                self.index += 1
                return self.evaluator.sum_range(letters, first, self._cell())
            return self.evaluator.value(letters, first)
        if self._peek() == "$":
            self.index += 1
        row = self._digits()
        return self.evaluator.value(self.sheet, f"{letters.upper()}{row}")

    def _sum_argument(self) -> tuple[str, str, str | None]:
        self._skip()
        if self._peek() == "'":
            return self._quoted_sheet_range()
        letters = self._letters()
        if self._peek() == "!":
            self.index += 1
            first = self._cell()
            if self._peek() == ":":
                self.index += 1
                return letters, first, self._cell()
            return letters, first, None
        if self._peek() == "$":
            self.index += 1
        row = self._digits()
        start = f"{letters.upper()}{row}"
        if self._peek() == ":":
            self.index += 1
            return self.sheet, start, self._cell()
        return self.sheet, start, None


class WorkbookEvaluator:
    def __init__(self, path: Path) -> None:
        self.workbook: Workbook = load_workbook(path, data_only=False)
        self.cache: dict[tuple[str, str], Decimal] = {}
        self.stack: set[tuple[str, str]] = set()

    def value(self, sheet: str, coord: str) -> Decimal:
        key = (sheet, coord.upper())
        if key in self.cache:
            return self.cache[key]
        if key in self.stack:
            raise FormulaError(f"circular reference at {sheet}!{coord}")
        cell = self.workbook[sheet][coord].value
        self.stack.add(key)
        try:
            parsed = self._coerce(sheet, coord, cell)
        finally:
            self.stack.remove(key)
        self.cache[key] = parsed
        return parsed

    def _coerce(self, sheet: str, coord: str, cell: object) -> Decimal:
        if cell is None:
            return Decimal(0)
        if isinstance(cell, str) and cell.startswith("="):
            return _Parser(cell, sheet, self).parse()
        if isinstance(cell, str):
            raise FormulaError(f"text in a numeric formula at {sheet}!{coord}: {cell}")
        return decimal_from_number(cell)

    def sum_range(self, sheet: str, start: str, end: str) -> Decimal:
        total = Decimal(0)
        for coord in _coordinates(start, end):
            cell = self.workbook[sheet][coord].value
            if isinstance(cell, str) and not cell.startswith("="):
                continue
            total += self.value(sheet, coord)
        return total

    def formulas(self) -> dict[tuple[str, str], Decimal]:
        results: dict[tuple[str, str], Decimal] = {}
        for worksheet in self.workbook.worksheets:
            for row in worksheet.iter_rows():
                for cell in row:
                    if isinstance(cell.value, str) and cell.value.startswith("="):
                        results[(worksheet.title, cell.coordinate)] = self.value(
                            worksheet.title, cell.coordinate
                        )
        return results


def _coordinates(start: str, end: str) -> list[str]:
    start_col, start_row = _split(start)
    end_col, end_row = _split(end)
    coords: list[str] = []
    for row in range(min(start_row, end_row), max(start_row, end_row) + 1):
        for col in range(min(start_col, end_col), max(start_col, end_col) + 1):
            coords.append(f"{get_column_letter(col)}{row}")
    return coords


def _split(coord: str) -> tuple[int, int]:
    letters = "".join(char for char in coord if char.isalpha())
    digits = "".join(char for char in coord if char.isdigit())
    return column_index_from_string(letters), int(digits)


def evaluate_workbook(path: Path) -> dict[tuple[str, str], Decimal]:
    """Return every formula cell in the workbook, evaluated from the stored inputs."""
    return WorkbookEvaluator(path).formulas()


def compare_to_model(path: Path, model: CompanyModel) -> list[str]:
    """Check formula results against the Python model. Returns problem strings."""
    evaluated = evaluate_workbook(path)
    problems: list[str] = []

    def money_cell(sheet: str, coord: str, expected: Decimal, label: str) -> None:
        got = money(evaluated[(sheet, coord)])
        if got != expected:
            problems.append(f"{label} {sheet}!{coord}: workbook {got} != model {expected}")

    def count_cell(sheet: str, coord: str, expected: int, label: str) -> None:
        got = evaluated[(sheet, coord)]
        if got != Decimal(expected):
            problems.append(f"{label} {sheet}!{coord}: workbook {got} != model {expected}")

    for index, month in enumerate(model.forecast):
        column = get_column_letter(index + 2)
        count_cell("Forecast", f"{column}7", month.beginning, month.label)
        count_cell("Forecast", f"{column}10", month.ending, month.label)
        money_cell("Forecast", f"{column}13", month.revenue, month.label)
        money_cell("Forecast", f"{column}14", month.cogs, month.label)
        money_cell("Forecast", f"{column}15", month.gross_profit, month.label)
        money_cell("Forecast", f"{column}25", month.people_cost, month.label)
        money_cell("Forecast", f"{column}26", month.other_opex, month.label)
        money_cell("Forecast", f"{column}27", month.total_opex, month.label)
        money_cell("Forecast", f"{column}28", month.operating_income, month.label)

    money_cell("Forecast", "N13", sum_money(model.forecast, "revenue"), "FY forecast revenue")
    money_cell("Forecast", "N27", sum_money(model.forecast, "total_opex"), "FY forecast opex")
    money_cell(
        "Forecast", "N28", sum_money(model.forecast, "operating_income"), "FY forecast income"
    )
    count_cell("Forecast", "N8", sum_count(model.forecast, "new"), "FY forecast new customers")
    count_cell(
        "Forecast", "N9", sum_count(model.forecast, "churned"), "FY forecast churned customers"
    )

    money_cell(
        "Budget-vs-Actual",
        "D11",
        money(sum_money(model.actuals, "revenue") - sum_money(model.budget, "revenue")),
        "FY revenue variance",
    )
    money_cell(
        "Budget-vs-Actual",
        "D16",
        money(sum_money(model.actuals, "total_opex") - sum_money(model.budget, "total_opex")),
        "FY opex variance",
    )
    money_cell(
        "Budget-vs-Actual",
        "D17",
        money(
            sum_money(model.actuals, "operating_income")
            - sum_money(model.budget, "operating_income")
        ),
        "FY operating-income variance",
    )
    money_cell(
        "Budget-vs-Actual",
        "D32",
        money(model.actuals[-1].revenue - model.budget[-1].revenue),
        "December revenue variance",
    )
    count_cell("Budget-vs-Actual", "C10", model.actuals[-1].ending, "December actual customers")
    count_cell("Budget-vs-Actual", "B10", model.budget[-1].ending, "December budget customers")
    money_cell("Summary", "F11", arr(model.forecast[-1]), "Forecast ARR")
    money_cell("Summary", "C11", arr(model.actuals[-1]), "Actual ARR")
    money_cell("Summary", "B11", arr(model.budget[-1]), "Budget ARR")
    money_cell(
        "Summary", "F20", sum_money(model.forecast, "operating_income"), "Summary forecast income"
    )
    money_cell(
        "Summary", "C20", sum_money(model.actuals, "operating_income"), "Summary actual income"
    )
    money_cell(
        "Summary", "B20", sum_money(model.budget, "operating_income"), "Summary budget income"
    )
    return problems
