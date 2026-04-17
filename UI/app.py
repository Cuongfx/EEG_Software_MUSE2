from __future__ import annotations

import sys

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

from .main_window import ModernMuseWindow


def _preferred_ui_font() -> QFont:
    candidates = [
        "SF Pro Text",
        ".SF NS Text",
        "Helvetica Neue",
        "Arial Unicode MS",
        "Arial",
    ]
    available = set(QFontDatabase.families())
    for family in candidates:
        if family in available:
            return QFont(family, 11)
    return QFont("", 11)


def run() -> int:
    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        app.setFont(_preferred_ui_font())
    window = ModernMuseWindow()
    window.show()
    result = app.exec()
    return result if owns_app else 0
