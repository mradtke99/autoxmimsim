"""Objective functions for spectrum comparison."""

from __future__ import annotations

import math

from autoxmimsim.spectrum import Spectrum


def normalized_rmse(target: Spectrum, candidate: Spectrum) -> float:
    """Return RMSE after normalizing both spectra to unit area."""

    target_norm = target.normalized()
    candidate_norm = candidate.normalized()
    if target_norm.energies != candidate_norm.energies:
        raise ValueError("target and candidate spectra must use the same energy grid")
    squared_error = sum(
        (target_count - candidate_count) ** 2
        for target_count, candidate_count in zip(target_norm.counts, candidate_norm.counts)
    )
    return math.sqrt(squared_error / len(target_norm.counts))
