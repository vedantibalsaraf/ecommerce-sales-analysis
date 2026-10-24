"""Tests for the final pipeline commands and dataset-generation guard."""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import main  # noqa: E402


class DatasetGenerationGuardTests(unittest.TestCase):
    def test_existing_dataset_is_not_regenerated(self):
        with tempfile.TemporaryDirectory() as folder:
            existing = Path(folder) / "sales_data.csv"
            existing.write_text("order_id\n", encoding="utf-8")
            with patch.object(main, "DATA_FILE", existing), patch.object(
                main, "generate"
            ) as generate_mock:
                self.assertEqual(main.ensure_raw_dataset(), 0)
                generate_mock.assert_not_called()

    def test_missing_dataset_is_generated(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder) / "sales_data.csv"
            with patch.object(main, "DATA_FILE", missing), patch.object(
                main, "generate", return_value=0
            ) as generate_mock:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main.ensure_raw_dataset(), 0)
                generate_mock.assert_called_once_with()

    def test_run_all_runs_stages_in_order(self):
        with tempfile.TemporaryDirectory() as folder:
            existing = Path(folder) / "sales_data.csv"
            existing.write_text("order_id\n", encoding="utf-8")
            with patch.object(main, "DATA_FILE", existing), patch.object(
                main, "ensure_raw_dataset", return_value=0
            ) as ensure, patch("src.data_cleaning.run_cleaning") as cleaning, patch(
                "src.analysis.run_analysis"
            ) as analysis, patch.object(main, "_generate_part3") as outputs:
                cleaning.return_value = Mock(output_rows=10)
                analysis.return_value = Mock()

                manager = Mock()
                manager.attach_mock(ensure, "ensure")
                manager.attach_mock(cleaning, "clean")
                manager.attach_mock(analysis, "analyse")
                manager.attach_mock(outputs, "outputs")

                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main.run_all(), 0)
                self.assertEqual(
                    [call[0] for call in manager.mock_calls],
                    ["ensure", "clean", "analyse", "outputs"],
                )


if __name__ == "__main__":
    unittest.main()
