"""XMI-MSIM input template handling."""

from __future__ import annotations

import copy
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from autoxmimsim.parameters import ParameterValues


XMSI_DOCTYPE = '<!DOCTYPE xmimsim SYSTEM "http://www.xmi.UGent.be/xml/xmimsim-1.0.dtd">'
BRONZE_LAYER_INDEX = 3
COPPER_LAYER_INDEX = 1
TIN_LAYER_INDEX = 2


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
