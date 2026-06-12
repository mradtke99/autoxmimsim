from __future__ import annotations

import unittest
from pathlib import Path

from autoxmimsim.backends import SimulationRequest, XmsiTemplateBackend
from autoxmimsim.xmsi import XmsiTemplate


FIXTURE = Path("tests") / "fixtures" / "CuSnBronze.xmsi"


class XmsiTemplateTests(unittest.TestCase):
    def test_summarizes_cusn_bronze_template(self) -> None:
        summary = XmsiTemplate.load(FIXTURE).summary()

        self.assertEqual(summary.n_photons_interval, 100000)
        self.assertEqual(summary.n_photons_line, 1000000)
        self.assertEqual(summary.d_sample_source, 102.0)
        self.assertEqual(len(summary.layers), 4)
        self.assertEqual(summary.layers[3].thickness, 0.5)
        self.assertEqual(summary.layers[3].elements[0].atomic_number, 29)
        self.assertEqual(summary.layers[3].elements[0].weight_fraction, 90.0)
        self.assertEqual(summary.layers[3].elements[1].atomic_number, 50)
        self.assertEqual(summary.layers[3].elements[1].weight_fraction, 10.0)

    def test_applies_bronze_candidate_parameters(self) -> None:
        template = XmsiTemplate.load(FIXTURE).clone()

        template.apply_parameters(
            {
                "bronze_cu_fraction": 85.0,
                "bronze_sn_fraction": 15.0,
                "bronze_thickness": 0.42,
                "d_sample_source": 98.0,
                "detector_window_z": 88.0,
            }
        )
        summary = template.summary()

        self.assertEqual(summary.d_sample_source, 98.0)
        self.assertEqual(summary.detector_window_z, 88.0)
        self.assertEqual(summary.layers[3].thickness, 0.42)
        self.assertEqual(summary.layers[3].elements[0].weight_fraction, 85.0)
        self.assertEqual(summary.layers[3].elements[1].weight_fraction, 15.0)

    def test_applies_generic_layer_parameters(self) -> None:
        template = XmsiTemplate.load(FIXTURE).clone()

        template.apply_parameters(
            {
                "layer_1_thickness": 0.0002,
                "layer_1_density": 8.5,
                "layer_3_z29_fraction": 80.0,
                "layer_3_z50_fraction": 20.0,
            }
        )
        summary = template.summary()

        self.assertEqual(summary.layers[1].thickness, 0.0002)
        self.assertEqual(summary.layers[1].density, 8.5)
        self.assertEqual(summary.layers[3].elements[0].weight_fraction, 80.0)
        self.assertEqual(summary.layers[3].elements[1].weight_fraction, 20.0)

    def test_suggests_first_non_air_layer_parameters(self) -> None:
        suggestions = XmsiTemplate.load(FIXTURE).parameter_suggestions()
        names = {suggestion.name for suggestion in suggestions}

        self.assertIn("layer_1_thickness", names)
        self.assertIn("layer_1_density", names)
        self.assertIn("layer_1_z29_fraction", names)
        self.assertIn("d_sample_source", names)

    def test_template_backend_renders_candidate_file(self) -> None:
        output_dir = Path("reports") / "test-xmsi-template"
        backend = XmsiTemplateBackend(template_path=FIXTURE, work_dir=output_dir)

        rendered = backend.render_input(
            SimulationRequest(
                parameters={
                    "bronze_cu_fraction": 80.0,
                    "bronze_sn_fraction": 20.0,
                    "bronze_thickness": 0.33,
                }
            ),
            name="candidate-test",
        )

        self.assertTrue(rendered.exists())
        self.assertIn("<!DOCTYPE xmimsim", rendered.read_text(encoding="utf-8"))
        summary = XmsiTemplate.load(rendered).summary()
        self.assertTrue(summary.outputfile.endswith("candidate-test.xmso"))
        self.assertEqual(summary.layers[3].thickness, 0.33)
        self.assertEqual(summary.layers[3].elements[0].weight_fraction, 80.0)
        self.assertEqual(summary.layers[3].elements[1].weight_fraction, 20.0)
