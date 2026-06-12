from __future__ import annotations

import unittest
from pathlib import Path

from autoxmimsim.objectives import interpolated_normalized_rmse
from autoxmimsim.spectrum import Spectrum, interpolate_to, load_measured_csv, load_measured_hdf5, load_measured_spectrum


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

    def test_loads_four_detector_hdf5_point(self) -> None:
        spectrum = load_measured_hdf5(Path("tests") / "fixtures" / "50cent1002.hdf5", point_index=1)

        self.assertEqual(len(spectrum.counts), 4096)
        self.assertEqual(spectrum.energies[0], 0.02)
        self.assertAlmostEqual(spectrum.energies[1] - spectrum.energies[0], 0.01)
        self.assertGreater(spectrum.total_counts, 0.0)

    def test_measured_loader_dispatches_hdf5(self) -> None:
        spectrum = load_measured_spectrum(
            Path("tests") / "fixtures" / "50cent1002.hdf5",
            hdf5_point_index=1,
            hdf5_reducer="mean",
        )

        self.assertEqual(len(spectrum.counts), 4096)
