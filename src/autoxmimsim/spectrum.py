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


def load_measured_csv(path: Path) -> Spectrum:
    """Load a measured spectrum CSV with energy and counts columns.

    The loader accepts either a header row such as ``energy,counts`` or raw
    two-column numeric rows. Extra columns are ignored.
    """

    energies: list[float] = []
    counts: list[float] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        columns = [column.strip() for column in line.split(",")]
        if len(columns) < 2:
            raise ValueError(f"invalid measured CSV row {line_number}: expected at least 2 columns")
        try:
            energy = float(columns[0])
            count = float(columns[1])
        except ValueError:
            if line_number == 1:
                continue
            raise
        energies.append(energy)
        counts.append(count)
    return Spectrum.from_sequences(energies, counts)


def interpolate_to(source: Spectrum, target_energies: tuple[float, ...]) -> Spectrum:
    """Linearly interpolate a spectrum onto a target energy grid."""

    if any(right <= left for left, right in zip(source.energies, source.energies[1:])):
        raise ValueError("source energies must be strictly increasing")
    counts = [_interpolate_count(source, energy) for energy in target_energies]
    return Spectrum(target_energies, tuple(counts))


def _interpolate_count(source: Spectrum, energy: float) -> float:
    if energy <= source.energies[0]:
        return source.counts[0]
    if energy >= source.energies[-1]:
        return source.counts[-1]
    for index in range(1, len(source.energies)):
        right_energy = source.energies[index]
        if energy <= right_energy:
            left_energy = source.energies[index - 1]
            left_count = source.counts[index - 1]
            right_count = source.counts[index]
            fraction = (energy - left_energy) / (right_energy - left_energy)
            return left_count + fraction * (right_count - left_count)
    return source.counts[-1]
