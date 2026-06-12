from __future__ import annotations

import io
import unittest
from unittest.mock import patch

from autoxmimsim.cli import main


class CliTests(unittest.TestCase):
    def test_main_returns_success(self) -> None:
        self.assertEqual(main([]), 0)

    def test_synthetic_demo_command_runs_workflow(self) -> None:
        with patch("autoxmimsim.cli.run_synthetic_recovery") as run_synthetic_recovery:
            best = unittest.mock.Mock(score=0.0, parameters={"fe_fraction": 0.65})
            result = unittest.mock.Mock(best=best)
            run_synthetic_recovery.return_value = (result, "report.html")

            with patch("sys.stdout", new=io.StringIO()):
                self.assertEqual(main(["synthetic-demo", "--output", "out"]), 0)
            run_synthetic_recovery.assert_called_once()

    def test_gui_command_launches_gui(self) -> None:
        with patch("autoxmimsim.gui.launch_gui") as launch_gui:
            self.assertEqual(main(["gui"]), 0)
            launch_gui.assert_called_once()

    def test_real_bronze_command_runs_workflow(self) -> None:
        with patch("autoxmimsim.cli.run_real_bronze_demo") as run_real_bronze_demo:
            best = unittest.mock.Mock(
                score=0.0,
                parameters={"tin_layer_thickness": 0.05},
                result=unittest.mock.Mock(run_id="candidate-001"),
            )
            result = unittest.mock.Mock(best=best)
            run_real_bronze_demo.return_value = (result, "report.html")

            with patch("sys.stdout", new=io.StringIO()):
                self.assertEqual(
                    main(
                        [
                            "run-real-bronze-demo",
                            "template.xmsi",
                            "--output",
                            "out",
                            "--target",
                            "copper_layer_thickness=0.00055",
                            "--target",
                            "tin_layer_thickness=0.05",
                            "--range",
                            "copper_layer_thickness=0.0001:0.001:3",
                            "--range",
                            "tin_layer_thickness=0.03:0.07:3",
                            "--evaluations",
                            "5",
                        ]
                    ),
                    0,
                )
            run_real_bronze_demo.assert_called_once()
            _, _, kwargs = run_real_bronze_demo.mock_calls[0]
            self.assertEqual(kwargs["target_parameters"]["copper_layer_thickness"], 0.00055)
            self.assertEqual(kwargs["parameter_space"].parameters[0].name, "copper_layer_thickness")
            self.assertEqual(kwargs["evaluations"], 5)
