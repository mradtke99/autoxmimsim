from __future__ import annotations

import unittest
from pathlib import Path

from autoxmimsim.backends import SimulationResult
from autoxmimsim.optimization import CandidateResult, OptimizationResult, UncertaintySummary
from autoxmimsim.reporting import write_recovery_report, write_spectrum_plot
from autoxmimsim.spectrum import Spectrum


class ReportingTests(unittest.TestCase):
    def test_spectrum_plot_uses_log_counts_scale(self) -> None:
        output_dir = Path("reports") / "test-reporting"
        target = Spectrum((1.0, 2.0, 3.0), (0.0, 10.0, 100.0))
        result = _result(target)

        plot_path = write_spectrum_plot(output_dir, target, result)

        html = plot_path.read_text(encoding="utf-8")
        self.assertIn('data-y-scale="log"', html)
        self.assertIn("logarithmic y scale", html)

    def test_recovery_report_keeps_residuals_linear(self) -> None:
        output_dir = Path("reports") / "test-reporting"
        target = Spectrum((1.0, 2.0, 3.0), (1.0, 10.0, 100.0))
        result = _result(target)

        report_path = write_recovery_report(output_dir, {"value": 1.0}, target, result)

        html = report_path.read_text(encoding="utf-8")
        self.assertIn('data-y-scale="log"', html)
        self.assertIn('data-y-scale="linear"', html)


def _result(spectrum: Spectrum) -> OptimizationResult:
    simulation = SimulationResult(
        spectrum=spectrum,
        parameters={"value": 1.0},
        run_id="candidate-000",
    )
    candidate = CandidateResult(parameters={"value": 1.0}, score=0.0, result=simulation)
    return OptimizationResult(
        best=candidate,
        history=(candidate,),
        uncertainty=UncertaintySummary(score_threshold=0.0, intervals={"value": (1.0, 1.0)}),
    )
