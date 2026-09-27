"""
SRM EEE Library Management System — Entry Point
Run: python main.py
"""

import sys
import os

# Add parent dir to path so 'library_app' is importable
sys.path.insert(0, os.path.dirname(__file__))

from PySide6.QtWidgets import QApplication, QSplashScreen, QLabel
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QFont, QColor

from library_app.database import initialize_db
from library_app.ui.main_window import MainWindow


def create_splash():
    """Create a simple splash screen."""
    pixmap = QPixmap(500, 300)
    pixmap.fill(QColor("#1E1E2E"))
    splash = QSplashScreen(pixmap)
    splash.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

    lbl = QLabel(splash)
    lbl.setText(
        "<div style='color:white;text-align:center;'>"
        "<p style='font-size:28px;font-weight:bold;margin:0;'>📚 SRM Library</p>"
        "<p style='font-size:14px;color:#9FA8DA;margin:8px 0 0;'>EEE Department</p>"
        "<p style='font-size:12px;color:#616161;margin:16px 0 0;'>Loading…</p>"
        "</div>"
    )
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setGeometry(0, 0, 500, 300)
    return splash


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SRM EEE Library")
    app.setOrganizationName("SRM Institute")

    # Show splash
    splash = create_splash()
    splash.show()
    app.processEvents()

    # Initialize database
    initialize_db()

    # Create main window
    window = MainWindow()

    # Close splash and show main window after brief delay
    def show_main():
        splash.finish(window)
        window.show()
        window.raise_()
        window.activateWindow()
        window.setWindowState(window.windowState() & ~Qt.WindowState.WindowMinimized)

    QTimer.singleShot(800, show_main)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
