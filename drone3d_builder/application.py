"""Application bootstrap."""

import sys

from PySide6.QtWidgets import QApplication

from .main_window import Drone3DBuilder


def run() -> int:
    """Create and run the Qt application."""

    app = QApplication(sys.argv)
    window = Drone3DBuilder()
    window.show()
    return app.exec()
