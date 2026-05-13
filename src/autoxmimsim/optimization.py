"""Baseline optimizers and uncertainty summaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from autoxmimsim.backends import SimulationBackend, SimulationRequest, SimulationResult
from autoxmimsim.parameters import ParameterSpace, ParameterValues
from autoxmimsim.spectrum import Spectrum


Objective = Callable[[Spectrum, Spectrum], float]


@dataclass(frozen=True)
class CandidateResult:
    parameters: ParameterValues
    score: float
    result: SimulationResult


@dataclass(frozen=True)
class UncertaintySummary:
    score_threshold: float
    intervals: dict[str, tuple[float, float]]


@dataclass(frozen=True)
class OptimizationResult:
    best: CandidateResult
    history: tuple[CandidateResult, ...]
    uncertainty: UncertaintySummary


def grid_search(
    backend: SimulationBackend,
    target: Spectrum,
    parameter_space: ParameterSpace,
    objective: Objective,
    uncertainty_ratio: float = 1.10,
    run_id_prefix: str = "candidate",
) -> OptimizationResult:
    """Evaluate every point in a finite grid and return the best candidate."""

    history: list[CandidateResult] = []
    for index, parameters in enumerate(parameter_space.grid()):
        run_id = f"{run_id_prefix}-{index:03d}"
        simulation = backend.simulate(SimulationRequest(parameters=parameters, run_id=run_id))
        score = objective(target, simulation.spectrum)
        history.append(CandidateResult(parameters=parameters, score=score, result=simulation))

    best = min(history, key=lambda candidate: candidate.score)
    threshold = best.score * uncertainty_ratio
    if best.score == 0:
        threshold = min(
            (candidate.score for candidate in history if candidate.score > 0),
            default=0.0,
        )
    near_best = [candidate for candidate in history if candidate.score <= threshold]
    intervals = _intervals(near_best or [best])
    return OptimizationResult(
        best=best,
        history=tuple(sorted(history, key=lambda candidate: candidate.score)),
        uncertainty=UncertaintySummary(score_threshold=threshold, intervals=intervals),
    )


def _intervals(candidates: list[CandidateResult]) -> dict[str, tuple[float, float]]:
    names = candidates[0].parameters.keys()
    intervals: dict[str, tuple[float, float]] = {}
    for name in names:
        values = [candidate.parameters[name] for candidate in candidates]
        intervals[name] = (min(values), max(values))
    return intervals
