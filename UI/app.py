from __future__ import annotations

import sys

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from .main_window import ModernMuseWindow


def run() -> int:
    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        app.setFont(QFont("Avenir Next", 11))
    window = ModernMuseWindow()
    window.show()
    result = app.exec()
    return result if owns_app else 0
