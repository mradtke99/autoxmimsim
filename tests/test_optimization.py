from __future__ import annotations

import unittest

from autoxmimsim.backends import SimulationRequest, SimulationResult
from autoxmimsim.optimization import bayesian_grid_search, grid_search
from autoxmimsim.parameters import Parameter, ParameterSpace
from autoxmimsim.spectrum import Spectrum


class RecordingBackend:
    def __init__(self) -> None:
        self.requests: list[SimulationRequest] = []

    def simulate(self, request: SimulationRequest) -> SimulationResult:
        self.requests.append(request)
        value = request.parameters["value"]
        return SimulationResult(
            spectrum=Spectrum((1.0,), (value,)),
            parameters=dict(request.parameters),
            run_id=request.run_id,
        )


class OptimizationTests(unittest.TestCase):
    def test_grid_search_generates_stable_candidate_run_ids(self) -> None:
        backend = RecordingBackend()
        target = Spectrum((1.0,), (1.0,))
        parameter_space = ParameterSpace((Parameter("value", 1.0, 3.0, 3),))

        result = grid_search(
            backend=backend,
            target=target,
            parameter_space=parameter_space,
            objective=lambda left, right: abs(left.counts[0] - right.counts[0]),
        )

        self.assertEqual([request.run_id for request in backend.requests], [
            "candidate-000",
            "candidate-001",
            "candidate-002",
        ])
        self.assertEqual(result.history[0].result.run_id, "candidate-000")

    def test_bayesian_grid_search_adaptively_limits_evaluations(self) -> None:
        backend = RecordingBackend()
        target = Spectrum((1.0,), (2.0,))
        parameter_space = ParameterSpace((Parameter("value", 1.0, 3.0, 3),))

        result = bayesian_grid_search(
            backend=backend,
            target=target,
            parameter_space=parameter_space,
            objective=lambda left, right: abs(left.counts[0] - right.counts[0]),
            evaluations=2,
            initial_evaluations=1,
        )

        self.assertEqual(len(backend.requests), 2)
        self.assertEqual([request.run_id for request in backend.requests], ["candidate-000", "candidate-001"])
        self.assertEqual(result.best.parameters, {"value": 2.0})
