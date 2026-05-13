"""HTML reporting for synthetic recovery runs."""

from __future__ import annotations

import html
import json
from pathlib import Path

from autoxmimsim.optimization import OptimizationResult
from autoxmimsim.parameters import ParameterValues
from autoxmimsim.spectrum import Spectrum


def write_recovery_report(
    output_dir: Path,
    target_parameters: ParameterValues,
    target_spectrum: Spectrum,
    result: OptimizationResult,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "synthetic-recovery-report.html"
    summary_path = output_dir / "synthetic-recovery-summary.json"

    summary = {
        "target_parameters": target_parameters,
        "best_parameters": result.best.parameters,
        "best_score": result.best.score,
        "best_artifacts": _stringify_artifacts(result.best.result.artifacts),
        "uncertainty_intervals": result.uncertainty.intervals,
        "evaluations": len(result.history),
        "candidates": [
            {
                "run_id": candidate.result.run_id,
                "parameters": candidate.parameters,
                "score": candidate.score,
                "artifacts": _stringify_artifacts(candidate.result.artifacts),
            }
            for candidate in result.history
        ],
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    report_path.write_text(
        _render_report(target_parameters, target_spectrum, result, summary_path.name),
        encoding="utf-8",
    )
    return report_path


def _render_report(
    target_parameters: ParameterValues,
    target_spectrum: Spectrum,
    result: OptimizationResult,
    summary_name: str,
) -> str:
    best_spectrum = result.best.result.spectrum
    rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(name)}</td>"
        f"<td>{target_parameters[name]:.6g}</td>"
        f"<td>{result.best.parameters[name]:.6g}</td>"
        f"<td>{result.best.parameters[name] - target_parameters[name]:.6g}</td>"
        f"<td>{result.uncertainty.intervals[name][0]:.6g} - {result.uncertainty.intervals[name][1]:.6g}</td>"
        "</tr>"
        for name in target_parameters
    )
    residuals = tuple(
        target_count - best_count
        for target_count, best_count in zip(target_spectrum.counts, best_spectrum.counts)
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>autoxmimsim synthetic recovery report</title>
  <style>
    body {{ font-family: Arial, sans-serif; line-height: 1.45; margin: 32px; color: #1f2933; }}
    h1, h2 {{ margin-bottom: 0.3rem; }}
    table {{ border-collapse: collapse; margin: 1rem 0; width: 100%; max-width: 900px; }}
    th, td {{ border: 1px solid #c9d1d9; padding: 0.45rem 0.6rem; text-align: right; }}
    th:first-child, td:first-child {{ text-align: left; }}
    th {{ background: #f3f5f7; }}
    .metric {{ display: inline-block; margin-right: 1.5rem; }}
    svg {{ max-width: 980px; width: 100%; height: auto; border: 1px solid #d8dee4; background: white; }}
    .target {{ stroke: #1f77b4; }}
    .best {{ stroke: #d62728; }}
    .residual {{ stroke: #2ca02c; }}
  </style>
</head>
<body>
  <h1>autoxmimsim synthetic recovery report</h1>
  <p>
    <span class="metric"><strong>Best score:</strong> {result.best.score:.8g}</span>
    <span class="metric"><strong>Evaluations:</strong> {len(result.history)}</span>
    <span class="metric"><strong>Machine summary:</strong> {html.escape(summary_name)}</span>
  </p>

  <h2>Recovered parameters</h2>
  <table>
    <thead>
      <tr><th>Parameter</th><th>Target</th><th>Recovered</th><th>Error</th><th>Near-best interval</th></tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>

  <h2>Target vs recovered spectrum</h2>
  {_svg_lines(target_spectrum.energies, [target_spectrum.counts, best_spectrum.counts], ["target", "best"])}

  <h2>Residuals</h2>
  {_svg_lines(target_spectrum.energies, [residuals], ["residual"])}
</body>
</html>
"""


def _stringify_artifacts(artifacts: dict[str, Path]) -> dict[str, str]:
    return {name: str(path) for name, path in artifacts.items()}


def _svg_lines(
    x_values: tuple[float, ...],
    series: list[tuple[float, ...]],
    classes: list[str],
    width: int = 980,
    height: int = 320,
) -> str:
    margin = 32
    min_x = min(x_values)
    max_x = max(x_values)
    all_y = [value for values in series for value in values]
    min_y = min(all_y)
    max_y = max(all_y)
    if min_y == max_y:
        min_y -= 1.0
        max_y += 1.0

    def scale_x(value: float) -> float:
        return margin + (value - min_x) * (width - 2 * margin) / (max_x - min_x)

    def scale_y(value: float) -> float:
        return height - margin - (value - min_y) * (height - 2 * margin) / (max_y - min_y)

    paths = []
    for values, class_name in zip(series, classes):
        points = " ".join(
            f"{scale_x(x_value):.2f},{scale_y(y_value):.2f}"
            for x_value, y_value in zip(x_values, values)
        )
        paths.append(
            f'<polyline class="{html.escape(class_name)}" points="{points}" '
            'fill="none" stroke-width="2" />'
        )
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img">'
        f'<line x1="{margin}" y1="{height - margin}" x2="{width - margin}" y2="{height - margin}" stroke="#8b949e" />'
        f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height - margin}" stroke="#8b949e" />'
        + "".join(paths)
        + "</svg>"
    )
