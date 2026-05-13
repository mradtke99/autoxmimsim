"""Command line interface for autoxmimsim."""

from __future__ import annotations

import argparse
from pathlib import Path

from autoxmimsim import __version__
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
        help="run a tiny real XMI-MSIM Cu/Sn bronze candidate comparison",
    )
    real_bronze.add_argument("template", type=Path)
    real_bronze.add_argument(
        "--output",
        type=Path,
        default=Path("reports") / "real-bronze-demo",
        help="directory for target, candidate, and report artifacts",
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
        result, report_path = run_real_bronze_demo(args.template, args.output)
        print(f"Best score: {result.best.score:.8g}")
        print(f"Best run: {result.best.result.run_id}")
        print("Best parameters:")
        for name, value in result.best.parameters.items():
            print(f"  {name}: {value:.6g}")
        print(f"Artifact root: {args.output}")
        print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
