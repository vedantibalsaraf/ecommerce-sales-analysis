"""Verify that the project imports only Python standard-library modules.

The optional Streamlit dashboard (``app.py``) is the only file allowed to
import a third-party package, so it is skipped here.
"""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_MODULES = {"main", "src", "data", "tests"}
DASHBOARD_PATH = PROJECT_ROOT / "app.py"


class StandardLibraryOnlyTests(unittest.TestCase):
    def test_all_imports_are_standard_library_or_local(self):
        allowed = set(sys.stdlib_module_names) | LOCAL_MODULES
        violations = []

        for path in PROJECT_ROOT.rglob("*.py"):
            if "__pycache__" in path.parts or path == DASHBOARD_PATH:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    if node.module:
                        names = [node.module]
                for name in names:
                    root_module = name.split(".")[0]
                    if root_module not in allowed:
                        violations.append(
                            f"{path.relative_to(PROJECT_ROOT)}: {name}"
                        )

        self.assertEqual(
            violations,
            [],
            "Non-standard-library imports found:\n" + "\n".join(violations),
        )


if __name__ == "__main__":
    unittest.main()
