"""Spectrum data structures."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Spectrum:
    """Energy-dispersive spectrum with matching energy and count arrays."""

    energies: tuple[float, ...]
    counts: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.energies) != len(self.counts):
            raise ValueError("energies and counts must have the same length")
        if not self.energies:
            raise ValueError("spectrum must contain at least one channel")

    @classmethod
    def from_sequences(cls, energies: list[float], counts: list[float]) -> "Spectrum":
        return cls(tuple(float(value) for value in energies), tuple(float(value) for value in counts))

    @property
    def total_counts(self) -> float:
        return sum(self.counts)

    def normalized(self) -> "Spectrum":
        total = self.total_counts
        if total <= 0:
            raise ValueError("cannot normalize a spectrum with non-positive total counts")
        return Spectrum(self.energies, tuple(count / total for count in self.counts))
