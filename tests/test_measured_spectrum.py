from __future__ import annotations

import unittest
from pathlib import Path

from autoxmimsim.objectives import interpolated_normalized_rmse
from autoxmimsim.spectrum import Spectrum, interpolate_to, load_measured_csv


class MeasuredSpectrumTests(unittest.TestCase):
    def test_loads_measured_csv_with_header(self) -> None:
        spectrum = load_measured_csv(Path("tests") / "fixtures" / "measured-spectrum.csv")

        self.assertEqual(spectrum.energies, (1.0, 2.0))
        self.assertEqual(spectrum.counts, (10.0, 11.0))

    def test_interpolates_spectrum_to_target_grid(self) -> None:
        source = Spectrum((1.0, 3.0), (10.0, 30.0))

        interpolated = interpolate_to(source, (1.0, 2.0, 3.0))

        self.assertEqual(interpolated.counts, (10.0, 20.0, 30.0))

    def test_interpolated_objective_accepts_different_grids(self) -> None:
        target = Spectrum((1.0, 2.0, 3.0), (10.0, 20.0, 30.0))
        candidate = Spectrum((1.0, 3.0), (10.0, 30.0))

        self.assertEqual(interpolated_normalized_rmse(target, candidate), 0.0)
