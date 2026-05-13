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
from autoxmimsim.optimization import CandidateResult, OptimizationResult, UncertaintySummary, grid_search
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
            },
            run_id="candidate",
        )
    )


REAL_BRONZE_TARGET: ParameterValues = {
    "copper_layer_thickness": 0.0001,
    "tin_layer_thickness": 0.05,
}

REAL_BRONZE_CANDIDATES: tuple[ParameterValues, ...] = (
    {
        "copper_layer_thickness": 0.0002,
        "tin_layer_thickness": 0.03,
    },
    {
        "copper_layer_thickness": 0.0001,
        "tin_layer_thickness": 0.05,
    },
    {
        "copper_layer_thickness": 0.001,
        "tin_layer_thickness": 0.10,
    },
)

SMOKE_PHOTONS: ParameterValues = {
    "n_photons_interval": 10.0,
    "n_photons_line": 100.0,
}


def run_real_bronze_demo(template_path: Path, output_dir: Path) -> tuple[OptimizationResult, Path]:
    backend = XmiMsimCliBackend(template_path=template_path, work_dir=output_dir, threads=1)
    target_parameters = dict(REAL_BRONZE_TARGET)
    target_simulation = backend.simulate(
        SimulationRequest(
            parameters={**target_parameters, **SMOKE_PHOTONS},
            run_id="target",
        )
    )

    history: list[CandidateResult] = []
    for index, candidate_parameters in enumerate(REAL_BRONZE_CANDIDATES):
        run_id = f"candidate-{index:03d}"
        simulation = backend.simulate(
            SimulationRequest(
                parameters={**candidate_parameters, **SMOKE_PHOTONS},
                run_id=run_id,
            )
        )
        score = normalized_rmse(target_simulation.spectrum, simulation.spectrum)
        history.append(
            CandidateResult(
                parameters=dict(candidate_parameters),
                score=score,
                result=simulation,
            )
        )

    sorted_history = tuple(sorted(history, key=lambda candidate: candidate.score))
    best = sorted_history[0]
    result = OptimizationResult(
        best=best,
        history=sorted_history,
        uncertainty=UncertaintySummary(
            score_threshold=best.score,
            intervals={name: (value, value) for name, value in best.parameters.items()},
        ),
    )
    report_path = write_recovery_report(
        output_dir,
        target_parameters,
        target_simulation.spectrum,
        result,
    )
    return result, report_path
