"""
Main application window — sidebar navigation shell
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget,
    QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon

from .dashboard import DashboardScreen
from .issue_return import IssueReturnScreen
from .books import BooksScreen
from .patrons import PatronsScreen
from .reports import ReportsScreen
from .settings import SettingsScreen
from ..utils.styles import MAIN_STYLE, BG_CARD, PRIMARY, TEXT_SECONDARY, BORDER


NAV_ITEMS = [
    ("🏠", "Dashboard",    0),
    ("📤", "Issue Book",   1),
    ("📥", "Return Book",  2),
    ("📚", "Books",        3),
    ("👥", "Patrons",      4),
    ("📊", "Reports",      5),
    ("⚙️",  "Settings",    6),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SRM EEE Library Management System")
        self.setMinimumSize(1200, 750)
        self.resize(1400, 860)
        self.setStyleSheet(MAIN_STYLE)

        self._nav_buttons = []
        self._build_ui()
        self._navigate(0)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ─── Sidebar ──────────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(210)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 20, 12, 20)
        sidebar_layout.setSpacing(4)

        # Logo / header
        logo_lbl = QLabel("📚 SRM Library")
        logo_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        logo_lbl.setStyleSheet(f"color: white; padding: 8px 4px 16px 4px;")
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(logo_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {BORDER}; margin-bottom: 8px;")
        sidebar_layout.addWidget(sep)

        # Nav buttons
        for icon, label, page_idx in NAV_ITEMS:
            btn = QPushButton(f"  {icon}  {label}")
            btn.setObjectName("nav_btn")
            btn.setMinimumHeight(42)
            btn.setFont(QFont("Segoe UI", 12))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=page_idx: self._navigate(idx))
            self._nav_buttons.append(btn)
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        # Version label
        ver_lbl = QLabel("v1.0  •  EEE Dept")
        ver_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px; padding: 4px;")
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(ver_lbl)

        root.addWidget(sidebar)

        # ─── Content Stack ────────────────────────────────────────────────
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        # Create all screens
        self.dashboard = DashboardScreen(
            on_issue=lambda: self._navigate(1),
            on_return=lambda: self._navigate(2),
        )
        self.issue_screen = IssueReturnScreen(mode="issue")
        self.return_screen = IssueReturnScreen(mode="return")
        self.books_screen = BooksScreen()
        self.patrons_screen = PatronsScreen()
        self.reports_screen = ReportsScreen()
        self.settings_screen = SettingsScreen()

        for screen in [self.dashboard, self.issue_screen, self.return_screen,
                       self.books_screen, self.patrons_screen,
                       self.reports_screen, self.settings_screen]:
            self.stack.addWidget(screen)

        # Connect issue/return signals to dashboard refresh
        self.issue_screen.book_issued.connect(self.dashboard.refresh)
        self.return_screen.book_returned.connect(self.dashboard.refresh)

    def _navigate(self, idx: int):
        self.stack.setCurrentIndex(idx)

        # Update nav button active state
        for i, btn in enumerate(self._nav_buttons):
            btn.setProperty("active", "true" if i == idx else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Auto-focus issue/return input
        if idx == 1:
            self.issue_screen.focus_book_input()
        elif idx == 2:
            self.return_screen.focus_book_input()
        elif idx == 5:
            self.reports_screen.refresh()
