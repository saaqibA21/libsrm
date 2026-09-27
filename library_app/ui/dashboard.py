"""
Dashboard screen — shows key stats and quick actions
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor
from datetime import datetime

from ..database import get_dashboard_stats, get_overdue_transactions, get_transaction_history
from ..utils.styles import (PRIMARY, DANGER, WARNING, SUCCESS, ACCENT,
                             BG_CARD, TEXT_PRIMARY, TEXT_SECONDARY, BORDER)


def make_stat_card(value, label, color=PRIMARY, icon=""):
    frame = QFrame()
    frame.setObjectName("card")
    frame.setMinimumHeight(110)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(18, 14, 18, 14)
    layout.setSpacing(4)

    icon_label = QLabel(icon)
    icon_label.setFont(QFont("Segoe UI Emoji", 22))
    icon_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

    val_label = QLabel(str(value))
    val_label.setObjectName("stat_number")
    val_label.setFont(QFont("Segoe UI", 28, QFont.Weight.ExtraBold))
    val_label.setStyleSheet(f"color: {color}; font-size: 28px;")

    lbl = QLabel(label.upper())
    lbl.setObjectName("stat_label")
    lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")

    layout.addWidget(icon_label)
    layout.addWidget(val_label)
    layout.addWidget(lbl)
    return frame, val_label


class DashboardScreen(QWidget):
    def __init__(self, parent=None, on_issue=None, on_return=None):
        super().__init__(parent)
        self.on_issue = on_issue
        self.on_return = on_return
        self._stat_labels = {}
        self._build_ui()
        self.refresh()

        # Auto-refresh every 30s
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(30000)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)

        # Header
        header = QHBoxLayout()
        title = QLabel("📚 Library Dashboard")
        title.setObjectName("title_label")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))

        self.date_label = QLabel()
        self.date_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._update_time()
        time_timer = QTimer(self)
        time_timer.timeout.connect(self._update_time)
        time_timer.start(60000)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.date_label)
        layout.addLayout(header)

        # Quick Action Buttons
        action_layout = QHBoxLayout()
        action_layout.setSpacing(12)

        btn_issue = QPushButton("📤  Issue Book")
        btn_issue.setObjectName("btn_success")
        btn_issue.setMinimumHeight(42)
        btn_issue.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        btn_issue.clicked.connect(lambda: self.on_issue() if self.on_issue else None)

        btn_return = QPushButton("📥  Return Book")
        btn_return.setObjectName("btn_warning")
        btn_return.setMinimumHeight(42)
        btn_return.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        btn_return.clicked.connect(lambda: self.on_return() if self.on_return else None)

        btn_refresh = QPushButton("🔄  Refresh")
        btn_refresh.setObjectName("btn_secondary")
        btn_refresh.setMinimumHeight(42)
        btn_refresh.clicked.connect(self.refresh)

        action_layout.addWidget(btn_issue)
        action_layout.addWidget(btn_return)
        action_layout.addStretch()
        action_layout.addWidget(btn_refresh)
        layout.addLayout(action_layout)

        # Stats Grid
        self.stats_grid = QGridLayout()
        self.stats_grid.setSpacing(14)

        stats_config = [
            ("total_books",    "📚", "Total Books",      PRIMARY),
            ("available_books","✅", "Available",        SUCCESS),
            ("issued_books",   "📤", "Issued",           ACCENT),
            ("total_patrons",  "👥", "Patrons",          "#7E57C2"),
            ("overdue",        "⚠️",  "Overdue",          DANGER),
            ("issued_today",   "📋", "Issued Today",     PRIMARY),
            ("returned_today", "↩️", "Returned Today",   SUCCESS),
            ("pending_fines",  "💰", "Pending Fines (₹)",WARNING),
        ]

        for idx, (key, icon, label, color) in enumerate(stats_config):
            card, val_lbl = make_stat_card(0, label, color, icon)
            self._stat_labels[key] = val_lbl
            self.stats_grid.addWidget(card, idx // 4, idx % 4)

        layout.addLayout(self.stats_grid)

        # Bottom section: Recent activity + Overdue list
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(16)

        # Recent Transactions
        recent_frame = QFrame()
        recent_frame.setObjectName("card")
        recent_layout = QVBoxLayout(recent_frame)
        recent_layout.setContentsMargins(14, 12, 14, 12)
        recent_lbl = QLabel("🕐 Recent Transactions")
        recent_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        recent_layout.addWidget(recent_lbl)

        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(4)
        self.recent_table.setHorizontalHeaderLabels(["Book", "Patron", "Action", "Date"])
        self.recent_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.recent_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.recent_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.recent_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.recent_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.recent_table.setAlternatingRowColors(True)
        self.recent_table.verticalHeader().setVisible(False)
        self.recent_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.recent_table.setMinimumHeight(220)
        recent_layout.addWidget(self.recent_table)
        bottom_layout.addWidget(recent_frame, 3)

        # Overdue List
        overdue_frame = QFrame()
        overdue_frame.setObjectName("card")
        overdue_layout = QVBoxLayout(overdue_frame)
        overdue_layout.setContentsMargins(14, 12, 14, 12)
        overdue_lbl = QLabel("🚨 Overdue Books")
        overdue_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        overdue_lbl.setStyleSheet(f"color: {DANGER};")
        overdue_layout.addWidget(overdue_lbl)

        self.overdue_table = QTableWidget()
        self.overdue_table.setColumnCount(3)
        self.overdue_table.setHorizontalHeaderLabels(["Patron", "Book", "Due Date"])
        self.overdue_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.overdue_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.overdue_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.overdue_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.overdue_table.setAlternatingRowColors(True)
        self.overdue_table.verticalHeader().setVisible(False)
        self.overdue_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.overdue_table.setMinimumHeight(220)
        overdue_layout.addWidget(self.overdue_table)
        bottom_layout.addWidget(overdue_frame, 2)

        layout.addLayout(bottom_layout)

    def _update_time(self):
        now = datetime.now()
        self.date_label.setText(now.strftime("%A, %d %B %Y  |  %I:%M %p"))

    def refresh(self):
        stats = get_dashboard_stats()
        for key, lbl in self._stat_labels.items():
            val = stats.get(key, 0)
            if key == "pending_fines":
                lbl.setText(f"₹{float(val):.0f}")
            else:
                lbl.setText(str(val))

        # Recent transactions
        history = get_transaction_history(limit=15)
        self.recent_table.setRowCount(0)
        for txn in history:
            row = self.recent_table.rowCount()
            self.recent_table.insertRow(row)
            title = txn.get("book_title", "")[:40]
            patron = txn.get("patron_name", "")
            action = "Returned" if txn["status"] == "returned" else "Issued"
            date = txn.get("return_date") or txn.get("issue_date", "")

            items = [title, patron, action, date]
            for col, text in enumerate(items):
                item = QTableWidgetItem(str(text))
                if action == "Issued":
                    item.setForeground(QColor(ACCENT))
                else:
                    item.setForeground(QColor(SUCCESS))
                self.recent_table.setItem(row, col, item)

        # Overdue
        overdue = get_overdue_transactions()
        self.overdue_table.setRowCount(0)
        for txn in overdue:
            row = self.overdue_table.rowCount()
            self.overdue_table.insertRow(row)
            items = [
                txn.get("patron_name", ""),
                txn.get("book_title", "")[:35],
                txn.get("due_date", ""),
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(str(text))
                item.setForeground(QColor(DANGER))
                self.overdue_table.setItem(row, col, item)
