"""Spectrum data structures."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


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


def load_measured_spectrum(
    path: Path,
    hdf5_point_index: int = 0,
    hdf5_reducer: Literal["sum", "mean"] = "sum",
    hdf5_energy_offset: float = 0.02,
    hdf5_energy_step: float = 0.01,
) -> Spectrum:
    """Load a measured spectrum from CSV or HDF5.

    HDF5 files are expected to contain ``entry/data/data`` with shape
    ``(points, spectra_per_point, channels)``.
    """

    if path.suffix.lower() in {".h5", ".hdf5", ".nxs", ".nx5"}:
        return load_measured_hdf5(
            path,
            point_index=hdf5_point_index,
            reducer=hdf5_reducer,
            energy_offset=hdf5_energy_offset,
            energy_step=hdf5_energy_step,
        )
    return load_measured_csv(path)


def load_measured_hdf5(
    path: Path,
    point_index: int = 0,
    reducer: Literal["sum", "mean"] = "sum",
    dataset_path: str = "entry/data/data",
    energy_offset: float = 0.02,
    energy_step: float = 0.01,
) -> Spectrum:
    """Load one measured point from an HDF5 spectrum stack."""

    try:
        import h5py
    except ImportError as exc:  # pragma: no cover - depends on runtime env
        raise RuntimeError("h5py is required to read measured HDF5 spectra") from exc

    with h5py.File(path, "r") as handle:
        if dataset_path not in handle:
            raise ValueError(f"missing HDF5 dataset: {dataset_path}")
        data = handle[dataset_path]
        if len(data.shape) != 3:
            raise ValueError(f"HDF5 dataset must have shape (points, spectra, channels), got {data.shape}")
        if point_index < 0 or point_index >= data.shape[0]:
            raise ValueError(f"point index {point_index} outside HDF5 point range 0..{data.shape[0] - 1}")
        spectra = data[point_index, :, :]
        if reducer == "sum":
            counts_array = spectra.sum(axis=0)
        elif reducer == "mean":
            counts_array = spectra.mean(axis=0)
        else:
            raise ValueError(f"unsupported HDF5 reducer: {reducer}")
    counts = [float(value) for value in counts_array]
    energies = [energy_offset + index * energy_step for index in range(len(counts))]
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
