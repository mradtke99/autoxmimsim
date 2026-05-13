"""Parameter-space primitives for inverse simulation."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product


ParameterValues = dict[str, float]


@dataclass(frozen=True)
class Parameter:
    """One optimizable scalar parameter."""

    name: str
    lower: float
    upper: float
    steps: int
    unit: str = ""

    def __post_init__(self) -> None:
        if self.steps < 2:
            raise ValueError("steps must be at least 2")
        if self.lower >= self.upper:
            raise ValueError("lower must be less than upper")

    def grid(self) -> tuple[float, ...]:
        spacing = (self.upper - self.lower) / (self.steps - 1)
        return tuple(self.lower + index * spacing for index in range(self.steps))


@dataclass(frozen=True)
class ParameterSpace:
    """Finite search grid for the baseline optimizer."""

    parameters: tuple[Parameter, ...]

    def __post_init__(self) -> None:
        names = [parameter.name for parameter in self.parameters]
        if len(set(names)) != len(names):
            raise ValueError("parameter names must be unique")

    def grid(self) -> tuple[ParameterValues, ...]:
        names = [parameter.name for parameter in self.parameters]
        values = [parameter.grid() for parameter in self.parameters]
        return tuple(dict(zip(names, point)) for point in product(*values))
