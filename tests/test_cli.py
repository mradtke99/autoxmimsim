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
                    main(["run-real-bronze-demo", "template.xmsi", "--output", "out"]),
                    0,
                )
            run_real_bronze_demo.assert_called_once()
