from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from autoxmimsim.backends import SimulationRequest, SimulationResult
from autoxmimsim.parameters import Parameter, ParameterSpace
from autoxmimsim.spectrum import Spectrum
from autoxmimsim.workflows import run_real_bronze_demo


TARGET = {
    "copper_layer_thickness": 0.00055,
    "tin_layer_thickness": 0.05,
}


class FakeBronzeBackend:
    requests: list[SimulationRequest] = []

    def __init__(self, template_path: Path, work_dir: Path, threads: int = 1) -> None:
        self.work_dir = work_dir
        FakeBronzeBackend.requests = []

    def simulate(self, request: SimulationRequest) -> SimulationResult:
        FakeBronzeBackend.requests.append(request)
        copper_error = abs(request.parameters["copper_layer_thickness"] - TARGET["copper_layer_thickness"])
        tin_error = abs(request.parameters["tin_layer_thickness"] - TARGET["tin_layer_thickness"])
        score_like_count = 10.0 + 1000.0 * copper_error + tin_error
        run_dir = self.work_dir / request.run_id
        return SimulationResult(
            spectrum=Spectrum((1.0, 2.0), (score_like_count, score_like_count + 1.0)),
            parameters=dict(request.parameters),
            run_id=request.run_id,
            artifacts={
                "xmsi": run_dir / f"{request.run_id}.xmsi",
                "xmso": run_dir / f"{request.run_id}.xmso",
                "csv": run_dir / f"{request.run_id}.csv",
            },
        )


class RealBronzeWorkflowTests(unittest.TestCase):
    def test_real_bronze_demo_runs_target_and_bayesian_candidates(self) -> None:
        output_dir = Path("reports") / "test-real-bronze-workflow"
        with patch("autoxmimsim.workflows.XmiMsimCliBackend", FakeBronzeBackend):
            result, report_path = run_real_bronze_demo(
                Path("tests") / "fixtures" / "CuSnBronze.xmsi",
                output_dir,
                target_parameters=TARGET,
                parameter_space=ParameterSpace(
                    (
                        Parameter("copper_layer_thickness", 0.0001, 0.001, 3),
                        Parameter("tin_layer_thickness", 0.03, 0.07, 3),
                    )
                ),
                evaluations=5,
            )

        self.assertEqual([request.run_id for request in FakeBronzeBackend.requests], [
            "target",
            "candidate-000",
            "candidate-001",
            "candidate-002",
            "candidate-003",
            "candidate-004",
        ])
        self.assertEqual(result.best.parameters, TARGET)
        self.assertTrue(report_path.exists())
        self.assertTrue((output_dir / "spectrum-comparison.html").exists())
