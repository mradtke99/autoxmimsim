"""XMI-MSIM input template handling."""

from __future__ import annotations

import copy
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from autoxmimsim.parameters import ParameterValues


XMSI_DOCTYPE = '<!DOCTYPE xmimsim SYSTEM "http://www.xmi.UGent.be/xml/xmimsim-1.0.dtd">'
BRONZE_LAYER_INDEX = 3
COPPER_LAYER_INDEX = 1
TIN_LAYER_INDEX = 2
GENERIC_THICKNESS_RE = re.compile(r"^layer_(\d+)_thickness$")
GENERIC_DENSITY_RE = re.compile(r"^layer_(\d+)_density$")
GENERIC_FRACTION_RE = re.compile(r"^layer_(\d+)_z(\d+)_fraction$")


@dataclass(frozen=True)
class ElementFraction:
    atomic_number: int
    weight_fraction: float


@dataclass(frozen=True)
class LayerSummary:
    index: int
    density: float
    thickness: float
    elements: tuple[ElementFraction, ...]


@dataclass(frozen=True)
class XmsiSummary:
    outputfile: str
    n_photons_interval: int
    n_photons_line: int
    d_sample_source: float
    detector_window_z: float
    layers: tuple[LayerSummary, ...]


@dataclass(frozen=True)
class ParameterSuggestion:
    name: str
    current: float
    lower: float
    upper: float
    steps: int = 5


class XmsiTemplate:
    """Mutable XMI-MSIM template with typed operations for common sample fields."""

    def __init__(self, tree: ET.ElementTree, source: Path | None = None) -> None:
        self._tree = tree
        self.source = source

    @classmethod
    def load(cls, path: Path) -> "XmsiTemplate":
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
        return cls(ET.parse(path, parser=parser), source=path)

    def clone(self) -> "XmsiTemplate":
        return XmsiTemplate(copy.deepcopy(self._tree), self.source)

    def summary(self) -> XmsiSummary:
        root = self._tree.getroot()
        return XmsiSummary(
            outputfile=_required_text(root, "general/outputfile"),
            n_photons_interval=int(_required_text(root, "general/n_photons_interval")),
            n_photons_line=int(_required_text(root, "general/n_photons_line")),
            d_sample_source=float(_required_text(root, "geometry/d_sample_source")),
            detector_window_z=float(_required_text(root, "geometry/p_detector_window/z")),
            layers=tuple(self._summarize_layers()),
        )

    def apply_parameters(self, parameters: ParameterValues) -> None:
        """Apply autoxmimsim parameter values to the XMSI template."""

        if "bronze_cu_fraction" in parameters or "bronze_sn_fraction" in parameters:
            cu_fraction = parameters.get(
                "bronze_cu_fraction",
                self._element_fraction(BRONZE_LAYER_INDEX, 29),
            )
            sn_fraction = parameters.get(
                "bronze_sn_fraction",
                self._element_fraction(BRONZE_LAYER_INDEX, 50),
            )
            self.set_bronze_composition(cu_fraction, sn_fraction)
        if "bronze_thickness" in parameters:
            self.set_layer_thickness(BRONZE_LAYER_INDEX, parameters["bronze_thickness"])
        if "copper_layer_thickness" in parameters:
            self.set_layer_thickness(COPPER_LAYER_INDEX, parameters["copper_layer_thickness"])
        if "tin_layer_thickness" in parameters:
            self.set_layer_thickness(TIN_LAYER_INDEX, parameters["tin_layer_thickness"])
        if "d_sample_source" in parameters:
            self._set_text("geometry/d_sample_source", parameters["d_sample_source"])
        if "detector_window_z" in parameters:
            self._set_text("geometry/p_detector_window/z", parameters["detector_window_z"])
        if "n_photons_interval" in parameters:
            self._set_text("general/n_photons_interval", parameters["n_photons_interval"])
        if "n_photons_line" in parameters:
            self._set_text("general/n_photons_line", parameters["n_photons_line"])
        self._apply_generic_layer_parameters(parameters)

    def set_outputfile(self, outputfile: Path | str) -> None:
        self._set_text("general/outputfile", str(outputfile))

    def set_bronze_composition(self, cu_fraction: float, sn_fraction: float) -> None:
        total = cu_fraction + sn_fraction
        if total <= 0:
            raise ValueError("bronze Cu/Sn fractions must have a positive sum")
        normalized_cu = 100.0 * cu_fraction / total
        normalized_sn = 100.0 * sn_fraction / total
        self._set_element_fraction(BRONZE_LAYER_INDEX, 29, normalized_cu)
        self._set_element_fraction(BRONZE_LAYER_INDEX, 50, normalized_sn)

    def set_layer_thickness(self, layer_index: int, thickness: float) -> None:
        if thickness <= 0:
            raise ValueError("layer thickness must be positive")
        layer = self._layer(layer_index)
        _required_child(layer, "thickness").text = _format_float(thickness)

    def set_layer_density(self, layer_index: int, density: float) -> None:
        if density <= 0:
            raise ValueError("layer density must be positive")
        layer = self._layer(layer_index)
        _required_child(layer, "density").text = _format_float(density)

    def parameter_suggestions(self, sample_layer_index: int | None = None) -> tuple[ParameterSuggestion, ...]:
        summary = self.summary()
        layer = summary.layers[sample_layer_index or self.first_sample_layer_index()]
        suggestions = [
            _bounded_suggestion(f"layer_{layer.index}_thickness", layer.thickness),
            _bounded_suggestion(f"layer_{layer.index}_density", layer.density),
        ]
        suggestions.extend(
            _fraction_suggestion(f"layer_{layer.index}_z{element.atomic_number}_fraction", element.weight_fraction)
            for element in layer.elements
        )
        suggestions.extend(
            (
                _bounded_suggestion("d_sample_source", summary.d_sample_source),
                _bounded_suggestion("detector_window_z", summary.detector_window_z),
            )
        )
        return tuple(suggestions)

    def first_sample_layer_index(self) -> int:
        layers = self.summary().layers
        for layer in layers:
            if layer.index != 0:
                return layer.index
        raise ValueError("template has no non-air sample layer")

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        xml_body = ET.tostring(self._tree.getroot(), encoding="unicode")
        path.write_text(
            f'<?xml version="1.0"?>\n{XMSI_DOCTYPE}\n{xml_body}\n',
            encoding="utf-8",
        )
        return path

    def _summarize_layers(self) -> list[LayerSummary]:
        summaries: list[LayerSummary] = []
        for index, layer in enumerate(self._layers()):
            elements = tuple(
                ElementFraction(
                    atomic_number=int(_required_text(element, "atomic_number")),
                    weight_fraction=float(_required_text(element, "weight_fraction")),
                )
                for element in layer.findall("element")
            )
            summaries.append(
                LayerSummary(
                    index=index,
                    density=float(_required_text(layer, "density")),
                    thickness=float(_required_text(layer, "thickness")),
                    elements=elements,
                )
            )
        return summaries

    def _set_element_fraction(
        self,
        layer_index: int,
        atomic_number: int,
        weight_fraction: float,
    ) -> None:
        layer = self._layer(layer_index)
        for element in layer.findall("element"):
            if int(_required_text(element, "atomic_number")) == atomic_number:
                _required_child(element, "weight_fraction").text = _format_float(weight_fraction)
                return
        raise ValueError(f"layer {layer_index} has no element with Z={atomic_number}")

    def _element_fraction(self, layer_index: int, atomic_number: int) -> float:
        layer = self._layer(layer_index)
        for element in layer.findall("element"):
            if int(_required_text(element, "atomic_number")) == atomic_number:
                return float(_required_text(element, "weight_fraction"))
        raise ValueError(f"layer {layer_index} has no element with Z={atomic_number}")

    def _set_text(self, path: str, value: float | int | str) -> None:
        element = _required_child(self._tree.getroot(), path)
        element.text = _format_float(value) if isinstance(value, float) else str(value)

    def _apply_generic_layer_parameters(self, parameters: ParameterValues) -> None:
        layer_fraction_updates: dict[int, dict[int, float]] = {}
        for name, value in parameters.items():
            thickness_match = GENERIC_THICKNESS_RE.match(name)
            if thickness_match:
                self.set_layer_thickness(int(thickness_match.group(1)), value)
                continue
            density_match = GENERIC_DENSITY_RE.match(name)
            if density_match:
                self.set_layer_density(int(density_match.group(1)), value)
                continue
            fraction_match = GENERIC_FRACTION_RE.match(name)
            if fraction_match:
                layer_index = int(fraction_match.group(1))
                atomic_number = int(fraction_match.group(2))
                layer_fraction_updates.setdefault(layer_index, {})[atomic_number] = value
        for layer_index, updates in layer_fraction_updates.items():
            self._set_normalized_layer_fractions(layer_index, updates)

    def _set_normalized_layer_fractions(self, layer_index: int, updates: dict[int, float]) -> None:
        layer = self._layer(layer_index)
        fractions = {
            int(_required_text(element, "atomic_number")): float(_required_text(element, "weight_fraction"))
            for element in layer.findall("element")
        }
        for atomic_number in updates:
            if atomic_number not in fractions:
                raise ValueError(f"layer {layer_index} has no element with Z={atomic_number}")
        fractions.update(updates)
        total = sum(fractions.values())
        if total <= 0:
            raise ValueError("layer element fractions must have a positive sum")
        for atomic_number, fraction in fractions.items():
            self._set_element_fraction(layer_index, atomic_number, 100.0 * fraction / total)

    def _layer(self, index: int) -> ET.Element:
        layers = self._layers()
        try:
            return layers[index]
        except IndexError as exc:
            raise ValueError(f"composition layer {index} does not exist") from exc

    def _layers(self) -> list[ET.Element]:
        return self._tree.getroot().findall("composition/layer")


def _required_child(element: ET.Element, path: str) -> ET.Element:
    child = element.find(path)
    if child is None:
        raise ValueError(f"missing required XMSI element: {path}")
    return child


def _required_text(element: ET.Element, path: str) -> str:
    text = _required_child(element, path).text
    if text is None:
        raise ValueError(f"missing required XMSI text: {path}")
    return text


def _format_float(value: float | int | str) -> str:
    if isinstance(value, str):
        return value
    return f"{value:.12g}"


def _bounded_suggestion(name: str, value: float) -> ParameterSuggestion:
    lower = value * 0.5 if value > 0 else -1.0
    upper = value * 1.5 if value > 0 else 1.0
    if lower == upper:
        upper = lower + 1.0
    return ParameterSuggestion(name=name, current=value, lower=lower, upper=upper)


def _fraction_suggestion(name: str, value: float) -> ParameterSuggestion:
    lower = max(0.0, value - 20.0)
    upper = min(100.0, value + 20.0)
    if lower == upper:
        lower = max(0.0, value - 1.0)
        upper = min(100.0, value + 1.0)
    return ParameterSuggestion(name=name, current=value, lower=lower, upper=upper)
