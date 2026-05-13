"""Baseline optimizers and uncertainty summaries."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, sqrt
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


def bayesian_grid_search(
    backend: SimulationBackend,
    target: Spectrum,
    parameter_space: ParameterSpace,
    objective: Objective,
    evaluations: int,
    initial_evaluations: int = 2,
    exploration: float = 1.25,
    length_scale: float = 0.45,
    uncertainty_ratio: float = 1.10,
    run_id_prefix: str = "candidate",
) -> OptimizationResult:
    """Adaptive finite-grid Bayesian optimization with an RBF GP surrogate.

    The search stays on the provided finite grid so every proposed point is a
    valid XMI-MSIM parameter set. Lower-confidence-bound acquisition is used
    because autoxmimsim minimizes spectrum mismatch scores.
    """

    grid = parameter_space.grid()
    if not grid:
        raise ValueError("parameter space must contain at least one point")
    evaluations = min(evaluations, len(grid))
    if evaluations < 1:
        raise ValueError("evaluations must be at least 1")
    initial_evaluations = max(1, min(initial_evaluations, evaluations))

    evaluated: list[int] = []
    history: list[CandidateResult] = []
    seed_indices = _seed_indices(len(grid), initial_evaluations)
    while len(history) < evaluations:
        if seed_indices:
            index = seed_indices.pop(0)
        else:
            index = _next_bayesian_index(
                grid,
                parameter_space,
                evaluated,
                history,
                exploration=exploration,
                length_scale=length_scale,
            )
        evaluated.append(index)
        history.append(
            _evaluate_candidate(
                backend,
                target,
                objective,
                grid[index],
                run_id=f"{run_id_prefix}-{len(history):03d}",
            )
        )

    return _optimization_result(history, uncertainty_ratio)


def _evaluate_candidate(
    backend: SimulationBackend,
    target: Spectrum,
    objective: Objective,
    parameters: ParameterValues,
    run_id: str,
) -> CandidateResult:
    simulation = backend.simulate(SimulationRequest(parameters=parameters, run_id=run_id))
    score = objective(target, simulation.spectrum)
    return CandidateResult(parameters=parameters, score=score, result=simulation)


def _optimization_result(history: list[CandidateResult], uncertainty_ratio: float) -> OptimizationResult:
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


def _seed_indices(grid_size: int, count: int) -> list[int]:
    if count == 1:
        return [grid_size // 2]
    indices = [
        round(index * (grid_size - 1) / (count - 1))
        for index in range(count)
    ]
    return list(dict.fromkeys(indices))


def _next_bayesian_index(
    grid: tuple[ParameterValues, ...],
    parameter_space: ParameterSpace,
    evaluated: list[int],
    history: list[CandidateResult],
    exploration: float,
    length_scale: float,
) -> int:
    evaluated_points = [_normalize_parameters(grid[index], parameter_space) for index in evaluated]
    scores = [candidate.score for candidate in history]
    best_index = -1
    best_acquisition = float("inf")
    for index, parameters in enumerate(grid):
        if index in evaluated:
            continue
        mean, variance = _gp_predict(
            evaluated_points,
            scores,
            _normalize_parameters(parameters, parameter_space),
            length_scale=length_scale,
        )
        acquisition = mean - exploration * sqrt(max(variance, 0.0))
        if acquisition < best_acquisition:
            best_acquisition = acquisition
            best_index = index
    if best_index < 0:
        raise ValueError("no unevaluated candidates remain")
    return best_index


def _normalize_parameters(parameters: ParameterValues, parameter_space: ParameterSpace) -> tuple[float, ...]:
    normalized: list[float] = []
    for parameter in parameter_space.parameters:
        value = parameters[parameter.name]
        normalized.append((value - parameter.lower) / (parameter.upper - parameter.lower))
    return tuple(normalized)


def _gp_predict(
    observed_x: list[tuple[float, ...]],
    observed_y: list[float],
    candidate_x: tuple[float, ...],
    length_scale: float,
    noise: float = 1e-9,
) -> tuple[float, float]:
    kernel = [
        [
            _rbf(left, right, length_scale) + (noise if row == col else 0.0)
            for col, right in enumerate(observed_x)
        ]
        for row, left in enumerate(observed_x)
    ]
    k_star = [_rbf(point, candidate_x, length_scale) for point in observed_x]
    alpha = _solve_linear_system(kernel, observed_y)
    v = _solve_linear_system(kernel, k_star)
    mean = sum(weight * value for weight, value in zip(k_star, alpha))
    variance = 1.0 - sum(weight * value for weight, value in zip(k_star, v))
    return mean, max(variance, 0.0)


def _rbf(left: tuple[float, ...], right: tuple[float, ...], length_scale: float) -> float:
    distance_squared = sum((left_value - right_value) ** 2 for left_value, right_value in zip(left, right))
    return exp(-0.5 * distance_squared / (length_scale * length_scale))


def _solve_linear_system(matrix: list[list[float]], values: list[float]) -> list[float]:
    size = len(values)
    augmented = [row[:] + [values[index]] for index, row in enumerate(matrix)]
    for col in range(size):
        pivot = max(range(col, size), key=lambda row: abs(augmented[row][col]))
        augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        pivot_value = augmented[col][col]
        if abs(pivot_value) < 1e-12:
            pivot_value = 1e-12
            augmented[col][col] = pivot_value
        for item in range(col, size + 1):
            augmented[col][item] /= pivot_value
        for row in range(size):
            if row == col:
                continue
            factor = augmented[row][col]
            for item in range(col, size + 1):
                augmented[row][item] -= factor * augmented[col][item]
    return [augmented[row][size] for row in range(size)]


def _intervals(candidates: list[CandidateResult]) -> dict[str, tuple[float, float]]:
    names = candidates[0].parameters.keys()
    intervals: dict[str, tuple[float, float]] = {}
    for name in names:
        values = [candidate.parameters[name] for candidate in candidates]
        intervals[name] = (min(values), max(values))
    return intervals
