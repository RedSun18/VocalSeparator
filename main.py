#!/usr/bin/env python3
"""
VocalSeparator - Professional macOS Vocal & Instrumental Separator
Entry point for the application.
"""

import sys
import os

# Ensure the project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtGui import QFont, QFontDatabase

from gui.main_window import MainWindow


def configure_app(app: QApplication) -> None:
    """Configure global application settings."""
    app.setApplicationName("VocalSeparator")
    app.setApplicationDisplayName("VocalSeparator")
    app.setOrganizationName("VocalSeparator")
    app.setOrganizationDomain("vocalseparator.app")
    app.setApplicationVersion("1.0.0")

    # Enable high DPI
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)


def main() -> int:
    """Application main function."""
    # Required for macOS to render properly
    os.environ.setdefault("QT_MAC_WANTS_LAYER", "1")

    app = QApplication(sys.argv)
    configure_app(app)

    # Load and apply stylesheet
    style_path = os.path.join(os.path.dirname(__file__), "assets", "style.qss")
    if os.path.exists(style_path):
        with open(style_path, "r") as f:
            app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
