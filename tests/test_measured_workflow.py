from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from autoxmimsim.backends import SimulationRequest, SimulationResult
from autoxmimsim.parameters import Parameter, ParameterSpace
from autoxmimsim.spectrum import Spectrum
from autoxmimsim.workflows import run_measured_optimization


class FakeMeasuredBackend:
    requests: list[SimulationRequest] = []

    def __init__(self, template_path: Path, work_dir: Path, threads: int = 1) -> None:
        self.work_dir = work_dir
        FakeMeasuredBackend.requests = []

    def simulate(self, request: SimulationRequest) -> SimulationResult:
        FakeMeasuredBackend.requests.append(request)
        value = request.parameters["value"]
        run_dir = self.work_dir / request.run_id
        return SimulationResult(
            spectrum=Spectrum((1.0, 2.0), (value, value + 1.0)),
            parameters=dict(request.parameters),
            run_id=request.run_id,
            artifacts={"csv": run_dir / f"{request.run_id}.csv"},
        )


class MeasuredWorkflowTests(unittest.TestCase):
    def test_measured_optimization_uses_csv_target_and_ranges(self) -> None:
        output_dir = Path("reports") / "test-measured-workflow"
        with patch("autoxmimsim.workflows.XmiMsimCliBackend", FakeMeasuredBackend):
            result, report_path = run_measured_optimization(
                Path("tests") / "fixtures" / "CuSnBronze.xmsi",
                Path("tests") / "fixtures" / "measured-spectrum.csv",
                output_dir,
                parameter_space=ParameterSpace((Parameter("value", 9.0, 11.0, 3),)),
                evaluations=2,
                initial_evaluations=1,
            )

        self.assertEqual([request.run_id for request in FakeMeasuredBackend.requests], [
            "candidate-000",
            "candidate-001",
        ])
        self.assertEqual(result.best.parameters, {"value": 10.0})
        self.assertTrue(report_path.exists())
        self.assertTrue((output_dir / "spectrum-comparison.html").exists())
