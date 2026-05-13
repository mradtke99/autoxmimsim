"""Command line interface for autoxmimsim."""

from __future__ import annotations

import argparse
from pathlib import Path

from autoxmimsim import __version__
from autoxmimsim.workflows import run_synthetic_recovery


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autoxmimsim",
        description="Automation helpers for XMI-MSIM workflows.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")

    synthetic_demo = subparsers.add_parser(
        "synthetic-demo",
        help="run the first synthetic recovery workflow with the fake backend",
    )
    synthetic_demo.add_argument(
        "--output",
        type=Path,
        default=Path("reports") / "synthetic-demo",
        help="directory for the generated report",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "synthetic-demo":
        result, report_path = run_synthetic_recovery(args.output)
        print(f"Best score: {result.best.score:.8g}")
        print("Recovered parameters:")
        for name, value in result.best.parameters.items():
            print(f"  {name}: {value:.6g}")
        print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
