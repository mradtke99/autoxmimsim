from __future__ import annotations

import unittest

from autoxmimsim.cli import main


class CliTests(unittest.TestCase):
    def test_main_returns_success(self) -> None:
        self.assertEqual(main([]), 0)
