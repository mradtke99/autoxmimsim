"""End-to-end workflows."""

from __future__ import annotations

from pathlib import Path

from autoxmimsim.backends import FakeXrfBackend, SimulationRequest
from autoxmimsim.objectives import normalized_rmse
from autoxmimsim.optimization import OptimizationResult, grid_search
from autoxmimsim.parameters import Parameter, ParameterSpace, ParameterValues
from autoxmimsim.reporting import write_recovery_report


DEFAULT_TARGET: ParameterValues = {
    "fe_fraction": 0.65,
    "thickness_um": 36.0,
    "detector_angle_deg": 45.0,
}


def default_parameter_space() -> ParameterSpace:
    return ParameterSpace(
        parameters=(
            Parameter("fe_fraction", lower=0.45, upper=0.85, steps=9),
            Parameter("thickness_um", lower=24.0, upper=48.0, steps=7, unit="um"),
            Parameter("detector_angle_deg", lower=35.0, upper=55.0, steps=5, unit="deg"),
        )
    )


def run_synthetic_recovery(output_dir: Path) -> tuple[OptimizationResult, Path]:
    backend = FakeXrfBackend()
    target = backend.simulate(SimulationRequest(parameters=DEFAULT_TARGET)).spectrum
    result = grid_search(
        backend=backend,
        target=target,
        parameter_space=default_parameter_space(),
        objective=normalized_rmse,
    )
    report_path = write_recovery_report(output_dir, DEFAULT_TARGET, target, result)
    return result, report_path
