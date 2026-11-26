import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="session")
def built(qapp, tmp_path_factory):
    """Every generated theme file, once, in a folder laid out like the system."""
    from pr7os import assets
    root = tmp_path_factory.mktemp("root")
    files = assets.build(root)
    return root, files
