"""End-to-end workflows."""

from __future__ import annotations

from pathlib import Path

from autoxmimsim.backends import (
    FakeXrfBackend,
    SimulationBackend,
    SimulationRequest,
    SimulationResult,
    XmiMsimCliBackend,
    XmsiTemplateBackend,
)
from autoxmimsim.objectives import interpolated_normalized_rmse, normalized_rmse
from autoxmimsim.optimization import CandidateResult, OptimizationResult, bayesian_grid_search, grid_search
from autoxmimsim.parameters import Parameter, ParameterSpace, ParameterValues
from autoxmimsim.reporting import write_recovery_report, write_spectrum_plot
from autoxmimsim.spectrum import Spectrum, interpolate_to, load_measured_csv
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
    write_spectrum_plot(output_dir, target, result)
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


def run_real_bronze_demo(
    template_path: Path,
    output_dir: Path,
    target_parameters: ParameterValues,
    parameter_space: ParameterSpace,
    evaluations: int,
    fixed_parameters: ParameterValues | None = None,
    initial_evaluations: int = 2,
) -> tuple[OptimizationResult, Path]:
    _validate_search_request(target_parameters, parameter_space)
    backend = _FixedParameterBackend(
        XmiMsimCliBackend(template_path=template_path, work_dir=output_dir, threads=1),
        fixed_parameters or {},
    )
    target_simulation = backend.simulate(
        SimulationRequest(
            parameters=target_parameters,
            run_id="target",
        )
    )
    result = bayesian_grid_search(
        backend=backend,
        target=target_simulation.spectrum,
        parameter_space=parameter_space,
        objective=normalized_rmse,
        evaluations=evaluations,
        initial_evaluations=initial_evaluations,
        run_id_prefix="candidate",
    )
    report_path = write_recovery_report(
        output_dir,
        target_parameters,
        target_simulation.spectrum,
        result,
    )
    write_spectrum_plot(output_dir, target_simulation.spectrum, result)
    return result, report_path


def run_measured_optimization(
    template_path: Path,
    measured_spectrum_path: Path,
    output_dir: Path,
    parameter_space: ParameterSpace,
    evaluations: int,
    fixed_parameters: ParameterValues | None = None,
    initial_evaluations: int = 2,
) -> tuple[OptimizationResult, Path]:
    measured_spectrum = load_measured_csv(measured_spectrum_path)
    backend = _FixedParameterBackend(
        XmiMsimCliBackend(template_path=template_path, work_dir=output_dir, threads=1),
        fixed_parameters or {},
    )
    result = bayesian_grid_search(
        backend=backend,
        target=measured_spectrum,
        parameter_space=parameter_space,
        objective=interpolated_normalized_rmse,
        evaluations=evaluations,
        initial_evaluations=initial_evaluations,
        run_id_prefix="candidate",
    )
    aligned_result = _align_result_spectra(result, measured_spectrum)
    report_path = write_recovery_report(
        output_dir,
        {},
        measured_spectrum,
        aligned_result,
    )
    write_spectrum_plot(output_dir, measured_spectrum, aligned_result)
    return aligned_result, report_path


def _validate_search_request(target_parameters: ParameterValues, parameter_space: ParameterSpace) -> None:
    target_names = set(target_parameters)
    range_names = {parameter.name for parameter in parameter_space.parameters}
    if target_names != range_names:
        missing_targets = sorted(range_names - target_names)
        missing_ranges = sorted(target_names - range_names)
        details = []
        if missing_targets:
            details.append(f"missing target values for: {', '.join(missing_targets)}")
        if missing_ranges:
            details.append(f"missing ranges for: {', '.join(missing_ranges)}")
        raise ValueError("; ".join(details))


class _FixedParameterBackend:
    def __init__(self, backend: SimulationBackend, fixed_parameters: ParameterValues) -> None:
        self._backend = backend
        self._fixed_parameters = dict(fixed_parameters)

    def simulate(self, request: SimulationRequest) -> SimulationResult:
        simulation = self._backend.simulate(
            SimulationRequest(
                parameters={**request.parameters, **self._fixed_parameters},
                run_id=request.run_id,
            )
        )
        return SimulationResult(
            spectrum=simulation.spectrum,
            parameters=dict(request.parameters),
            run_id=simulation.run_id,
            artifacts=simulation.artifacts,
        )


def _align_result_spectra(result: OptimizationResult, target: Spectrum) -> OptimizationResult:
    history = tuple(
        CandidateResult(
            parameters=candidate.parameters,
            score=candidate.score,
            result=SimulationResult(
                spectrum=interpolate_to(candidate.result.spectrum, target.energies),
                parameters=candidate.result.parameters,
                run_id=candidate.result.run_id,
                artifacts=candidate.result.artifacts,
            ),
        )
        for candidate in result.history
    )
    best = next(candidate for candidate in history if candidate.result.run_id == result.best.result.run_id)
    return OptimizationResult(best=best, history=history, uncertainty=result.uncertainty)
