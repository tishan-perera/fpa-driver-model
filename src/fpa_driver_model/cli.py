"""Command line for the synthetic FP&A model. No API key, no network."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fpa_driver_model import __version__
from fpa_driver_model.chart import render_chart
from fpa_driver_model.commentary import draft_commentary
from fpa_driver_model.paths import workbook_path
from fpa_driver_model.report import render_report
from fpa_driver_model.review import Decision, approval_path, decide, review_status
from fpa_driver_model.synthetic import load_model
from fpa_driver_model.tieout import FormulaError, compare_to_model
from fpa_driver_model.verify_workbook import main as verify_main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fpa-model",
        description=(
            "Driver-based FP&A model for fictional Fairhaven Metrics LLC. "
            "Commentary is off unless you pass --draft-commentary. No API key."
        ),
    )
    parser.add_argument("--version", action="version", version=f"fpa-model {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="Roll the forecast and print actual versus budget")
    run.add_argument(
        "--draft-commentary",
        action="store_true",
        help="Assemble a local variance draft. Off by default. Does not call a hosted model.",
    )
    run.add_argument("-o", "--output", type=Path, help="Write the draft to this file")

    chart = commands.add_parser("chart", help="Write the revenue chart from a model run")
    chart.add_argument("--output", type=Path, required=True)

    verify = commands.add_parser("verify", help="Recompute the workbook and tie out its formulas")
    verify.add_argument("workbook", nargs="?", type=Path)

    approve = commands.add_parser("approve", help="Record an analyst approval of a draft")
    approve.add_argument("draft", type=Path)
    approve.add_argument("--reviewer", required=True)
    approve.add_argument("--note", default="")

    reject = commands.add_parser("reject", help="Record an analyst rejection of a draft")
    reject.add_argument("draft", type=Path)
    reject.add_argument("--reviewer", required=True)
    reject.add_argument("--note", default="")

    status = commands.add_parser(
        "status", help="Show whether a draft is pending, approved, rejected, or stale"
    )
    status.add_argument("draft", type=Path)

    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            return _run(args.draft_commentary, args.output)
        if args.command == "chart":
            destination = render_chart(load_model(), args.output)
            print(destination)
            return 0
        if args.command == "verify":
            return _verify(args.workbook)
        if args.command == "approve":
            return _decide(args.draft, args.reviewer, args.note, "approved")
        if args.command == "reject":
            return _decide(args.draft, args.reviewer, args.note, "rejected")
        if args.command == "status":
            return _status(args.draft)
    except (ValueError, OSError, FileNotFoundError) as exc:
        print(exc, file=sys.stderr)
        return 2
    parser.error(f"unknown command {args.command}")
    return 2


def _run(draft: bool, output: Path | None) -> int:
    model = load_model()
    commentary = draft_commentary(model) if draft else None
    print(render_report(model, commentary=commentary), end="")
    if commentary is None:
        return 0
    if output is None:
        print(commentary, end="")
        return 0
    output.write_text(commentary, encoding="utf-8")
    print(f"Wrote draft to {output}")
    print('Status: pending. Approve with: fpa-model approve DRAFT --reviewer "Your name"')
    return 0


def _verify(workbook: Path | None) -> int:
    path = workbook if workbook is not None else workbook_path()
    code = verify_main([str(path)])
    if code != 0:
        return code
    try:
        problems = compare_to_model(path, load_model())
    except FormulaError as exc:
        print("FORMULA TIE-OUT FAILED")
        print("-", exc)
        return 1
    if problems:
        print("FORMULA TIE-OUT FAILED")
        for problem in problems:
            print("-", problem)
        return 1
    print("Formula tie-out passed. Workbook formulas match the Python model.")
    return 0


def _decide(draft: Path, reviewer: str, note: str, status: Decision) -> int:
    destination = decide(draft, reviewer=reviewer, note=note, status=status)
    print(f"{status} {draft}")
    print(f"Record: {destination}")
    return 0


def _status(draft: Path) -> int:
    if not draft.is_file():
        raise FileNotFoundError(f"draft not found: {draft}")
    state = review_status(draft)
    print(state)
    if state in {"approved", "rejected"}:
        payload = json.loads(approval_path(draft).read_text(encoding="utf-8"))
        print(f"reviewer: {payload['reviewer']}")
        if payload.get("note"):
            print(f"note: {payload['note']}")
    if state == "stale":
        print("The draft changed after the decision.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
