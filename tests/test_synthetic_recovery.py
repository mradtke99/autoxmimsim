from __future__ import annotations

import unittest
from pathlib import Path

from autoxmimsim.backends import FakeXrfBackend, SimulationRequest
from autoxmimsim.objectives import normalized_rmse
from autoxmimsim.workflows import DEFAULT_TARGET, run_synthetic_recovery


class SyntheticRecoveryTests(unittest.TestCase):
    def test_fake_backend_is_deterministic(self) -> None:
        backend = FakeXrfBackend()

        first = backend.simulate(SimulationRequest(parameters=DEFAULT_TARGET))
        second = backend.simulate(SimulationRequest(parameters=DEFAULT_TARGET))

        self.assertEqual(first.spectrum, second.spectrum)

    def test_normalized_rmse_is_zero_for_identical_spectra(self) -> None:
        backend = FakeXrfBackend()
        spectrum = backend.simulate(SimulationRequest(parameters=DEFAULT_TARGET)).spectrum

        self.assertEqual(normalized_rmse(spectrum, spectrum), 0.0)

    def test_synthetic_recovery_finds_known_truth_and_report(self) -> None:
        output_dir = Path("reports") / "test-synthetic-recovery"
        result, report_path = run_synthetic_recovery(output_dir)

        self.assertEqual(result.best.parameters, DEFAULT_TARGET)
        self.assertEqual(result.best.score, 0.0)
        self.assertTrue(report_path.exists())
        self.assertTrue((output_dir / "synthetic-recovery-summary.json").exists())
