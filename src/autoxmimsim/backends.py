"""Simulation backend interfaces and deterministic test backend."""

from __future__ import annotations

import math
import os
import subprocess
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Protocol, Sequence

from autoxmimsim.parameters import ParameterValues
from autoxmimsim.spectrum import Spectrum, load_xmimsim_csv
from autoxmimsim.xmsi import XmsiTemplate


@dataclass(frozen=True)
class SimulationRequest:
    parameters: ParameterValues
    run_id: str = "candidate"


@dataclass(frozen=True)
class SimulationResult:
    spectrum: Spectrum
    parameters: ParameterValues
    run_id: str = "candidate"
    artifacts: dict[str, Path] = field(default_factory=dict)


class SimulationBackend(Protocol):
    def simulate(self, request: SimulationRequest) -> SimulationResult:
        """Run one forward simulation."""


class FakeXrfBackend:
    """Fast deterministic backend with XRF-like peaks for synthetic recovery tests."""

    def __init__(self, channels: int = 401, max_energy_kev: float = 20.0) -> None:
        if channels < 3:
            raise ValueError("channels must be at least 3")
        self._energies = tuple(
            index * max_energy_kev / (channels - 1) for index in range(channels)
        )

    def simulate(self, request: SimulationRequest) -> SimulationResult:
        fe_fraction = request.parameters["fe_fraction"]
        thickness_um = request.parameters["thickness_um"]
        detector_angle_deg = request.parameters.get("detector_angle_deg", 45.0)

        angle_scale = 0.75 + 0.25 * math.sin(math.radians(detector_angle_deg))
        thickness_scale = 1.0 - math.exp(-thickness_um / 16.0)
        attenuation = math.exp(-thickness_um / 95.0)

        counts: list[float] = []
        for energy in self._energies:
            background = 12.0 + 0.22 * thickness_um + 0.6 * math.exp(-energy / 7.0)
            fe_peak = 720.0 * fe_fraction * thickness_scale * self._gaussian(energy, 6.40, 0.18)
            cu_peak = (
                620.0
                * (1.0 - fe_fraction)
                * thickness_scale
                * attenuation
                * self._gaussian(energy, 8.05, 0.22)
            )
            scatter = 95.0 * angle_scale * self._gaussian(energy, 11.5, 0.75)
            counts.append(background + fe_peak + cu_peak + scatter)

        return SimulationResult(
            spectrum=Spectrum(self._energies, tuple(counts)),
            parameters=dict(request.parameters),
            run_id=request.run_id,
        )

    @staticmethod
    def _gaussian(x_value: float, center: float, sigma: float) -> float:
        return math.exp(-0.5 * ((x_value - center) / sigma) ** 2)


class XmsiTemplateBackend:
    """Backend phase that renders candidate XMSI inputs without executing XMI-MSIM."""

    def __init__(self, template_path: Path, work_dir: Path) -> None:
        self.template_path = template_path
        self.work_dir = work_dir

    def render_input(self, request: SimulationRequest, name: str | None = None) -> Path:
        run_id = name or request.run_id
        run_dir = self.work_dir / run_id
        template = XmsiTemplate.load(self.template_path).clone()
        xmsi_path = run_dir / f"{run_id}.xmsi"
        xmso_path = run_dir / f"{run_id}.xmso"
        template.apply_parameters(request.parameters)
        template.set_outputfile(xmso_path)
        return template.write(xmsi_path)

    def simulate(self, request: SimulationRequest) -> SimulationResult:
        xmsi_path = self.render_input(request)
        raise NotImplementedError(
            "XmsiTemplateBackend rendered "
            f"{xmsi_path}, but executing XMI-MSIM is not implemented yet"
        )


class XmiMsimCliBackend(XmsiTemplateBackend):
    """Run rendered XMSI inputs with the installed XMI-MSIM command line tools."""

    def __init__(
        self,
        template_path: Path,
        work_dir: Path,
        xmimsim_cli: Path = Path(r"C:\Program Files\XMI-MSIM 64-bit\Bin\xmimsim-cli.exe"),
        xmso2csv: Path = Path(r"C:\Program Files\XMI-MSIM 64-bit\Bin\xmso2csv.exe"),
        threads: int = 1,
        timeout_seconds: float = 300.0,
        runner=subprocess.run,
    ) -> None:
        super().__init__(template_path=template_path, work_dir=work_dir)
        self.xmimsim_cli = xmimsim_cli
        self.xmso2csv = xmso2csv
        self.threads = threads
        self.timeout_seconds = timeout_seconds
        self._runner = runner

    def simulate(self, request: SimulationRequest) -> SimulationResult:
        run_id = request.run_id
        run_dir = self.work_dir / run_id
        xmsi_path = self.render_input(request)
        xmso_path = run_dir / f"{run_id}.xmso"
        csv_path = run_dir / f"{run_id}.csv"

        self._run(
            [
                str(self.xmimsim_cli),
                "--enable-default-seeds",
                f"--set-threads={self.threads}",
                str(xmsi_path),
            ]
        )
        self._run([str(self.xmso2csv), str(xmso_path), str(csv_path)])

        return SimulationResult(
            spectrum=load_xmimsim_csv(csv_path),
            parameters=dict(request.parameters),
            run_id=run_id,
            artifacts={"xmsi": xmsi_path, "xmso": xmso_path, "csv": csv_path},
        )

    def _run(self, command: Sequence[str]) -> None:
        try:
            completed = self._runner(
                command,
                env=_xmimsim_env(),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            raise RuntimeError(
                "XMI-MSIM command timed out after "
                f"{self.timeout_seconds:g} seconds: {' '.join(command)}\n"
                f"stdout:\n{stdout}\nstderr:\n{stderr}"
            ) from exc
        if completed.returncode != 0:
            raise RuntimeError(
                "XMI-MSIM command failed: "
                f"{' '.join(command)}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
            )


def _xmimsim_env() -> dict[str, str]:
    env = os.environ.copy()
    install_root = Path(r"C:\Program Files\XMI-MSIM 64-bit")
    extra_paths = [
        install_root / "Bin",
        install_root / "Lib",
        install_root / "GTK",
    ]
    env["PATH"] = env.get("PATH", "") + os.pathsep + os.pathsep.join(str(path) for path in extra_paths)
    return env
