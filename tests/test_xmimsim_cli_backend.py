from __future__ import annotations

import unittest
from dataclasses import dataclass
from pathlib import Path

from autoxmimsim.backends import SimulationRequest, XmiMsimCliBackend
from autoxmimsim.spectrum import load_xmimsim_csv


FIXTURE = Path("tests") / "fixtures" / "CuSnBronze.xmsi"


@dataclass
class Completed:
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


class FakeRunner:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.commands: list[list[str]] = []

    def __call__(self, command, **kwargs) -> Completed:
        self.commands.append(list(command))
        if str(command[0]).endswith("xmso2csv.exe"):
            csv_path = Path(command[2])
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            csv_path.write_text("0,0.02,1.0,2.0\n1,0.03,3.0,4.0\n", encoding="utf-8")
        return Completed()


class XmiMsimCliBackendTests(unittest.TestCase):
    def test_loads_final_intensity_column_from_csv(self) -> None:
        csv_path = Path("reports") / "test-cli-backend" / "sample.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        csv_path.write_text("0,1.0,2.0,3.0\n1,2.0,4.0,6.0\n", encoding="utf-8")

        spectrum = load_xmimsim_csv(csv_path)

        self.assertEqual(spectrum.energies, (1.0, 2.0))
        self.assertEqual(spectrum.counts, (3.0, 6.0))

    def test_cli_backend_renders_runs_converts_and_loads_spectrum(self) -> None:
        output_dir = Path("reports") / "test-cli-backend"
        runner = FakeRunner(output_dir)
        backend = XmiMsimCliBackend(
            template_path=FIXTURE,
            work_dir=output_dir,
            runner=runner,
        )

        result = backend.simulate(
            SimulationRequest(
                parameters={
                    "bronze_cu_fraction": 88.0,
                    "bronze_sn_fraction": 12.0,
                    "n_photons_interval": 10.0,
                    "n_photons_line": 100.0,
                }
            )
        )

        self.assertEqual(len(runner.commands), 2)
        self.assertTrue(str(runner.commands[0][0]).endswith("xmimsim-cli.exe"))
        self.assertTrue(str(runner.commands[1][0]).endswith("xmso2csv.exe"))
        self.assertEqual(result.spectrum.counts, (2.0, 4.0))
        self.assertTrue(result.artifacts["xmsi"].exists())
        self.assertEqual(result.artifacts["csv"], output_dir / "candidate.csv")
