"""Pytest session fixtures: expose project root to `sys.path` and
create a single `QApplication` for the duration of the test run."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PyQt5.QtWidgets import QApplication
_app = QApplication.instance() or QApplication(sys.argv)
