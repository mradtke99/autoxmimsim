"""Spectrum data structures."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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


def load_xmimsim_csv(path: Path) -> Spectrum:
    """Load a spectrum from an XMI-MSIM CSV export.

    XMI-MSIM CSV rows contain channel, energy, and one or more intensity columns.
    autoxmimsim uses the energy column and the final intensity column as the
    candidate spectrum for direct comparison.
    """

    energies: list[float] = []
    counts: list[float] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        columns = [column.strip() for column in line.split(",")]
        if len(columns) < 3:
            raise ValueError(f"invalid XMI-MSIM CSV row {line_number}: expected at least 3 columns")
        energies.append(float(columns[1]))
        counts.append(float(columns[-1]))
    return Spectrum.from_sequences(energies, counts)
