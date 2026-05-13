"""End-to-end workflows."""

from __future__ import annotations

from pathlib import Path

from autoxmimsim.backends import (
    FakeXrfBackend,
    SimulationRequest,
    SimulationResult,
    XmiMsimCliBackend,
    XmsiTemplateBackend,
)
from autoxmimsim.objectives import normalized_rmse
from autoxmimsim.optimization import OptimizationResult, grid_search
from autoxmimsim.parameters import Parameter, ParameterSpace, ParameterValues
from autoxmimsim.reporting import write_recovery_report
from autoxmimsim.xmsi import XmsiSummary, XmsiTemplate


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


def inspect_xmsi_template(template_path: Path) -> XmsiSummary:
    return XmsiTemplate.load(template_path).summary()


def render_bronze_candidate(template_path: Path, output_dir: Path) -> Path:
    backend = XmsiTemplateBackend(template_path=template_path, work_dir=output_dir)
    return backend.render_input(
        SimulationRequest(
            parameters={
                "bronze_cu_fraction": 88.0,
                "bronze_sn_fraction": 12.0,
                "bronze_thickness": 0.45,
                "d_sample_source": 102.0,
                "detector_window_z": 100.0,
            }
        ),
        name="bronze-candidate",
    )


def run_xmimsim_smoke(template_path: Path, output_dir: Path) -> SimulationResult:
    backend = XmiMsimCliBackend(template_path=template_path, work_dir=output_dir, threads=1)
    return backend.simulate(
        SimulationRequest(
            parameters={
                "bronze_cu_fraction": 88.0,
                "bronze_sn_fraction": 12.0,
                "bronze_thickness": 0.45,
                "n_photons_interval": 10.0,
                "n_photons_line": 100.0,
            }
        )
    )
