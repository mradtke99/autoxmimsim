"""Command line interface for autoxmimsim."""

from __future__ import annotations

import argparse
from pathlib import Path

from autoxmimsim import __version__
from autoxmimsim.parameters import Parameter, ParameterSpace, ParameterValues
from autoxmimsim.workflows import (
    inspect_xmsi_template,
    render_bronze_candidate,
    run_real_bronze_demo,
    run_xmimsim_smoke,
    run_synthetic_recovery,
)


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

    subparsers.add_parser(
        "gui",
        help="launch the desktop GUI for Bayesian XMI-MSIM searches",
    )

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
    inspect_template = subparsers.add_parser(
        "inspect-template",
        help="summarize an XMI-MSIM .xmsi template",
    )
    inspect_template.add_argument("template", type=Path)

    render_template = subparsers.add_parser(
        "render-template",
        help="render a modified Cu/Sn bronze candidate .xmsi from a template",
    )
    render_template.add_argument("template", type=Path)
    render_template.add_argument(
        "--output",
        type=Path,
        default=Path("reports") / "xmsi-template",
        help="directory for the rendered candidate input",
    )
    run_template = subparsers.add_parser(
        "run-template-smoke",
        help="run a low-photon XMI-MSIM smoke simulation from a template",
    )
    run_template.add_argument("template", type=Path)
    run_template.add_argument(
        "--output",
        type=Path,
        default=Path("reports") / "xmimsim-smoke",
        help="directory for rendered XMSI, XMSO, and CSV artifacts",
    )
    real_bronze = subparsers.add_parser(
        "run-real-bronze-demo",
        help="run a tiny real XMI-MSIM Cu/Sn bronze Bayesian optimization demo",
    )
    real_bronze.add_argument("template", type=Path)
    real_bronze.add_argument(
        "--output",
        type=Path,
        default=Path("reports") / "real-bronze-demo",
        help="directory for target, candidate, and report artifacts",
    )
    real_bronze.add_argument(
        "--target",
        action="append",
        required=True,
        metavar="NAME=VALUE",
        help="synthetic target parameter value; repeat for each varied parameter",
    )
    real_bronze.add_argument(
        "--range",
        action="append",
        required=True,
        metavar="NAME=LOWER:UPPER:STEPS",
        help="Bayesian search range; repeat for each varied parameter",
    )
    real_bronze.add_argument(
        "--evaluations",
        type=int,
        required=True,
        help="number of Bayesian candidate simulations to run",
    )
    real_bronze.add_argument(
        "--initial-evaluations",
        type=int,
        default=2,
        help="number of space-filling seed simulations before acquisition starts",
    )
    real_bronze.add_argument(
        "--n-photons-interval",
        type=float,
        default=10.0,
        help="fixed XMI-MSIM interval photon count for each simulation",
    )
    real_bronze.add_argument(
        "--n-photons-line",
        type=float,
        default=100.0,
        help="fixed XMI-MSIM line photon count for each simulation",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "gui":
        from autoxmimsim.gui import launch_gui

        launch_gui()
    elif args.command == "synthetic-demo":
        result, report_path = run_synthetic_recovery(args.output)
        print(f"Best score: {result.best.score:.8g}")
        print("Recovered parameters:")
        for name, value in result.best.parameters.items():
            print(f"  {name}: {value:.6g}")
        print(f"Report: {report_path}")
        print(f"Plot: {args.output / 'spectrum-comparison.html'}")
    elif args.command == "inspect-template":
        summary = inspect_xmsi_template(args.template)
        print(f"Output file: {summary.outputfile}")
        print(f"Photons interval: {summary.n_photons_interval}")
        print(f"Photons line: {summary.n_photons_line}")
        print(f"Sample-source distance: {summary.d_sample_source}")
        print(f"Detector window z: {summary.detector_window_z}")
        print("Composition layers:")
        for layer in summary.layers:
            elements = ", ".join(
                f"Z={element.atomic_number}: {element.weight_fraction:.6g}%"
                for element in layer.elements
            )
            print(
                f"  {layer.index}: thickness={layer.thickness:.6g}, "
                f"density={layer.density:.6g}, {elements}"
            )
    elif args.command == "render-template":
        rendered = render_bronze_candidate(args.template, args.output)
        print(f"Rendered template: {rendered}")
    elif args.command == "run-template-smoke":
        result = run_xmimsim_smoke(args.template, args.output)
        print(f"Channels: {len(result.spectrum.counts)}")
        print(f"Total counts: {result.spectrum.total_counts:.8g}")
        for name, path in result.artifacts.items():
            print(f"{name.upper()}: {path}")
    elif args.command == "run-real-bronze-demo":
        try:
            target_parameters = _parse_target_values(args.target)
            parameter_space = _parse_parameter_space(args.range)
        except ValueError as exc:
            parser.error(str(exc))
        result, report_path = run_real_bronze_demo(
            args.template,
            args.output,
            target_parameters=target_parameters,
            parameter_space=parameter_space,
            evaluations=args.evaluations,
            initial_evaluations=args.initial_evaluations,
            fixed_parameters={
                "n_photons_interval": args.n_photons_interval,
                "n_photons_line": args.n_photons_line,
            },
        )
        print(f"Best score: {result.best.score:.8g}")
        print(f"Best run: {result.best.result.run_id}")
        print("Best parameters:")
        for name, value in result.best.parameters.items():
            print(f"  {name}: {value:.6g}")
        print(f"Artifact root: {args.output}")
        print(f"Report: {report_path}")
        print(f"Plot: {args.output / 'spectrum-comparison.html'}")
    return 0


def _parse_target_values(values: list[str]) -> ParameterValues:
    parsed: ParameterValues = {}
    for value in values:
        name, raw_number = _split_once(value, "=", "target")
        if name in parsed:
            raise ValueError(f"duplicate target parameter: {name}")
        parsed[name] = float(raw_number)
    return parsed


def _parse_parameter_space(values: list[str]) -> ParameterSpace:
    parameters: list[Parameter] = []
    names: set[str] = set()
    for value in values:
        name, raw_range = _split_once(value, "=", "range")
        if name in names:
            raise ValueError(f"duplicate range parameter: {name}")
        parts = raw_range.split(":")
        if len(parts) != 3:
            raise ValueError(f"range must be NAME=LOWER:UPPER:STEPS: {value}")
        lower, upper, steps = parts
        parameters.append(Parameter(name=name, lower=float(lower), upper=float(upper), steps=int(steps)))
        names.add(name)
    return ParameterSpace(tuple(parameters))


def _split_once(value: str, delimiter: str, label: str) -> tuple[str, str]:
    if delimiter not in value:
        raise ValueError(f"{label} must contain '{delimiter}': {value}")
    name, raw_value = value.split(delimiter, 1)
    if not name or not raw_value:
        raise ValueError(f"{label} must be complete: {value}")
    return name, raw_value


if __name__ == "__main__":
    raise SystemExit(main())
