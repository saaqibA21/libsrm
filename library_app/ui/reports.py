"""
Reports & Analytics screen
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QFileDialog, QMessageBox, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from ..database import (
    get_overdue_transactions, get_all_active_transactions,
    get_transaction_history, get_most_borrowed_books,
    get_most_active_patrons, get_dashboard_stats, mark_fine_paid,
    get_setting
)
from ..utils.styles import (PRIMARY, DANGER, SUCCESS, WARNING, ACCENT,
                             TEXT_SECONDARY, BG_CARD)
from ..utils.email_utils import (send_email, build_overdue_email, build_due_reminder_email)

from datetime import datetime


class ReportsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header
        header = QHBoxLayout()
        title = QLabel("📊 Reports & Analytics")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))

        btn_refresh = QPushButton("🔄 Refresh All")
        btn_refresh.setObjectName("btn_secondary")
        btn_refresh.clicked.connect(self.refresh)

        btn_export = QPushButton("📄 Export Report")
        btn_export.clicked.connect(self._export_report)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(btn_refresh)
        header.addWidget(btn_export)
        layout.addLayout(header)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_overdue_tab(), "⚠️ Overdue")
        self.tabs.addTab(self._build_active_tab(), "📤 Currently Issued")
        self.tabs.addTab(self._build_history_tab(), "🕐 Transaction History")
        self.tabs.addTab(self._build_top_books_tab(), "🏆 Most Borrowed")
        self.tabs.addTab(self._build_top_patrons_tab(), "🌟 Active Patrons")
        layout.addWidget(self.tabs)

    # ─── Overdue Tab ────────────────────────────────────────────────────────────

    def _build_overdue_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        toolbar = QHBoxLayout()
        self.overdue_count_lbl = QLabel("")
        self.overdue_count_lbl.setStyleSheet(f"color: {DANGER}; font-weight: 700;")
        btn_email_all = QPushButton("📧 Email All Overdue")
        btn_email_all.setObjectName("btn_danger")
        btn_email_all.clicked.connect(self._email_all_overdue)
        btn_mark_paid = QPushButton("✅ Mark Fine Paid")
        btn_mark_paid.setObjectName("btn_success")
        btn_mark_paid.clicked.connect(self._mark_fine_paid)
        toolbar.addWidget(self.overdue_count_lbl)
        toolbar.addStretch()
        toolbar.addWidget(btn_mark_paid)
        toolbar.addWidget(btn_email_all)
        layout.addLayout(toolbar)

        self.overdue_table = QTableWidget()
        self.overdue_table.setColumnCount(8)
        self.overdue_table.setHorizontalHeaderLabels([
            "Patron", "Reg. No.", "Type", "Book Title", "Issue Date", "Due Date", "Overdue Days", "Fine (₹)"
        ])
        self.overdue_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.overdue_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.overdue_table.setAlternatingRowColors(True)
        self.overdue_table.verticalHeader().setVisible(False)
        self.overdue_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.overdue_table)
        return widget

    def _build_active_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        toolbar = QHBoxLayout()
        self.active_count_lbl = QLabel("")
        self.active_count_lbl.setStyleSheet(f"color: {ACCENT}; font-weight: 700;")
        btn_remind = QPushButton("📧 Send Due Reminders")
        btn_remind.clicked.connect(self._send_due_reminders)
        toolbar.addWidget(self.active_count_lbl)
        toolbar.addStretch()
        toolbar.addWidget(btn_remind)
        layout.addLayout(toolbar)

        self.active_table = QTableWidget()
        self.active_table.setColumnCount(6)
        self.active_table.setHorizontalHeaderLabels([
            "Patron", "Reg. No.", "Book Title", "Issue Date", "Due Date", "Days Left"
        ])
        self.active_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.active_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.active_table.setAlternatingRowColors(True)
        self.active_table.verticalHeader().setVisible(False)
        self.active_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.active_table)
        return widget

    def _build_history_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([
            "ID", "Patron", "Book", "Issue Date", "Due Date", "Return Date", "Status"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.history_table)
        return widget

    def _build_top_books_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        self.top_books_table = QTableWidget()
        self.top_books_table.setColumnCount(4)
        self.top_books_table.setHorizontalHeaderLabels(["Rank", "Book Title", "Authors", "Times Borrowed"])
        self.top_books_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.top_books_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.top_books_table.setAlternatingRowColors(True)
        self.top_books_table.verticalHeader().setVisible(False)
        layout.addWidget(self.top_books_table)
        return widget

    def _build_top_patrons_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        self.top_patrons_table = QTableWidget()
        self.top_patrons_table.setColumnCount(4)
        self.top_patrons_table.setHorizontalHeaderLabels(["Rank", "Name", "Reg. No.", "Books Borrowed"])
        self.top_patrons_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.top_patrons_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.top_patrons_table.setAlternatingRowColors(True)
        self.top_patrons_table.verticalHeader().setVisible(False)
        layout.addWidget(self.top_patrons_table)
        return widget

    # ─── Data Loading ───────────────────────────────────────────────────────────

    def refresh(self):
        self._load_overdue()
        self._load_active()
        self._load_history()
        self._load_top_books()
        self._load_top_patrons()

    def _load_overdue(self):
        overdue = get_overdue_transactions()
        self.overdue_table.setRowCount(0)
        today = datetime.now()
        fine_rate = float(get_setting("fine_per_day", "2.0"))

        for txn in overdue:
            row = self.overdue_table.rowCount()
            self.overdue_table.insertRow(row)
            due_date = datetime.strptime(txn["due_date"], "%Y-%m-%d")
            overdue_days = (today - due_date).days
            fine = overdue_days * fine_rate

            txn["_id"] = txn["id"]
            vals = [
                txn.get("patron_name", ""),
                txn.get("register_number", ""),
                txn.get("patron_type", "").title(),
                txn.get("book_title", ""),
                txn.get("issue_date", ""),
                txn.get("due_date", ""),
                str(overdue_days),
                f"₹{fine:.2f}",
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                item.setData(Qt.ItemDataRole.UserRole, txn["id"])
                item.setForeground(QColor(DANGER))
                if col == 7:
                    item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                self.overdue_table.setItem(row, col, item)

        self.overdue_count_lbl.setText(f"🚨 {len(overdue)} overdue book(s)")

    def _load_active(self):
        active = get_all_active_transactions()
        self.active_table.setRowCount(0)
        today = datetime.now()

        for txn in active:
            row = self.active_table.rowCount()
            self.active_table.insertRow(row)
            due_date = datetime.strptime(txn["due_date"], "%Y-%m-%d")
            days_left = (due_date - today).days
            color = DANGER if days_left < 0 else (WARNING if days_left <= 3 else SUCCESS)

            vals = [
                txn.get("patron_name", ""),
                txn.get("register_number", ""),
                txn.get("book_title", ""),
                txn.get("issue_date", ""),
                txn.get("due_date", ""),
                f"{'OVERDUE' if days_left < 0 else str(days_left) + ' days'}",
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                item.setData(Qt.ItemDataRole.UserRole, txn["id"])
                if col == 5:
                    item.setForeground(QColor(color))
                    item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                self.active_table.setItem(row, col, item)

        self.active_count_lbl.setText(f"📤 {len(active)} book(s) currently issued")

    def _load_history(self):
        history = get_transaction_history(200)
        self.history_table.setRowCount(0)
        for txn in history:
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)
            status = txn.get("status", "")
            color = SUCCESS if status == "returned" else ACCENT
            vals = [
                str(txn["id"]),
                txn.get("patron_name", ""),
                txn.get("book_title", ""),
                txn.get("issue_date", ""),
                txn.get("due_date", ""),
                txn.get("return_date", "") or "—",
                status.upper(),
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                if col == 6:
                    item.setForeground(QColor(color))
                    item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                self.history_table.setItem(row, col, item)

    def _load_top_books(self):
        books = get_most_borrowed_books(20)
        self.top_books_table.setRowCount(0)
        for rank, book in enumerate(books, 1):
            row = self.top_books_table.rowCount()
            self.top_books_table.insertRow(row)
            vals = [
                f"#{rank}",
                book.get("title", ""),
                book.get("authors", "") or "—",
                str(book.get("borrow_count", 0)),
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                if rank <= 3:
                    item.setForeground(QColor(WARNING))
                    item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                self.top_books_table.setItem(row, col, item)

    def _load_top_patrons(self):
        patrons = get_most_active_patrons(20)
        self.top_patrons_table.setRowCount(0)
        for rank, p in enumerate(patrons, 1):
            row = self.top_patrons_table.rowCount()
            self.top_patrons_table.insertRow(row)
            vals = [
                f"#{rank}",
                p.get("name", ""),
                p.get("register_number", ""),
                str(p.get("borrow_count", 0)),
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                if rank <= 3:
                    item.setForeground(QColor(WARNING))
                    item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                self.top_patrons_table.setItem(row, col, item)

    # ─── Actions ────────────────────────────────────────────────────────────────

    def _email_all_overdue(self):
        overdue = get_overdue_transactions()
        if not overdue:
            QMessageBox.information(self, "No Overdue", "No overdue books.")
            return

        smtp_host = get_setting("email_host", "smtp.gmail.com")
        smtp_port = int(get_setting("email_port", "587"))
        smtp_user = get_setting("email_user", "")
        smtp_pass = get_setting("email_password", "")
        lib_name = get_setting("library_name", "SRM EEE Library")
        fine_rate = float(get_setting("fine_per_day", "2.0"))

        if not smtp_user or not smtp_pass:
            QMessageBox.warning(self, "Email Not Configured",
                                "Please configure email settings in Settings → Email.")
            return

        # Group by patron
        patron_books: dict[str, list] = {}
        for txn in overdue:
            email = txn.get("patron_email", "")
            if not email:
                continue
            key = f"{email}|{txn.get('patron_name', '')}"
            patron_books.setdefault(key, [])
            patron_books[key].append(txn)

        sent = 0
        failed = 0
        for key, books in patron_books.items():
            email, name = key.split("|", 1)
            body = build_overdue_email(name, books, fine_rate, lib_name)
            success, err = send_email(email, f"[{lib_name}] Overdue Book Notice",
                                      body, smtp_host, smtp_port, smtp_user, smtp_pass)
            if success:
                sent += 1
            else:
                failed += 1

        QMessageBox.information(self, "Emails Sent",
                                f"✅ Sent: {sent}\n❌ Failed: {failed}")

    def _send_due_reminders(self):
        from datetime import timedelta
        active = get_all_active_transactions()
        today = datetime.now()
        remind_within = 3  # days

        smtp_host = get_setting("email_host", "smtp.gmail.com")
        smtp_port = int(get_setting("email_port", "587"))
        smtp_user = get_setting("email_user", "")
        smtp_pass = get_setting("email_password", "")
        lib_name = get_setting("library_name", "SRM EEE Library")

        if not smtp_user or not smtp_pass:
            QMessageBox.warning(self, "Email Not Configured",
                                "Please configure email settings in Settings → Email.")
            return

        patron_books: dict[str, list] = {}
        for txn in active:
            due = datetime.strptime(txn["due_date"], "%Y-%m-%d")
            days_left = (due - today).days
            if 0 <= days_left <= remind_within:
                email = txn.get("patron_email", "")
                if not email:
                    continue
                key = f"{email}|{txn.get('patron_name', '')}"
                patron_books.setdefault(key, [])
                patron_books[key].append(txn)

        if not patron_books:
            QMessageBox.information(self, "No Reminders",
                                    f"No books due within {remind_within} days with email addresses.")
            return

        sent = failed = 0
        for key, books in patron_books.items():
            email, name = key.split("|", 1)
            body = build_due_reminder_email(name, books, lib_name)
            success, err = send_email(email, f"[{lib_name}] Book Return Reminder",
                                      body, smtp_host, smtp_port, smtp_user, smtp_pass)
            if success:
                sent += 1
            else:
                failed += 1

        QMessageBox.information(self, "Reminders Sent",
                                f"✅ Sent: {sent}\n❌ Failed: {failed}")

    def _mark_fine_paid(self):
        row = self.overdue_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select", "Select an overdue record first.")
            return
        txn_id = self.overdue_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        mark_fine_paid(txn_id)
        self._load_overdue()

    def _export_report(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Report", "library_report.txt", "Text Files (*.txt);;All Files (*)"
        )
        if not filepath:
            return

        stats = get_dashboard_stats()
        overdue = get_overdue_transactions()
        active = get_all_active_transactions()
        top_books = get_most_borrowed_books(10)
        fine_rate = float(get_setting("fine_per_day", "2.0"))
        today = datetime.now()

        lines = [
            "=" * 60,
            "SRM EEE DEPARTMENT LIBRARY — REPORT",
            f"Generated: {today.strftime('%d %B %Y, %I:%M %p')}",
            "=" * 60,
            "",
            "SUMMARY",
            "-" * 40,
            f"Total Books        : {stats['total_books']}",
            f"Available          : {stats['available_books']}",
            f"Currently Issued   : {stats['issued_books']}",
            f"Total Patrons      : {stats['total_patrons']}",
            f"Overdue Books      : {stats['overdue']}",
            f"Issued Today       : {stats['issued_today']}",
            f"Returned Today     : {stats['returned_today']}",
            "",
            "OVERDUE BOOKS",
            "-" * 40,
        ]

        for txn in overdue:
            due = datetime.strptime(txn["due_date"], "%Y-%m-%d")
            days = (today - due).days
            fine = days * fine_rate
            lines.append(
                f"{txn['patron_name']} ({txn['register_number']}) — "
                f"{txn['book_title']} — Due: {txn['due_date']} — "
                f"{days} days overdue — Fine: ₹{fine:.2f}"
            )

        lines += ["", "TOP 10 MOST BORROWED BOOKS", "-" * 40]
        for rank, b in enumerate(top_books, 1):
            lines.append(f"{rank}. {b['title']} — {b['borrow_count']} times")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        QMessageBox.information(self, "Exported", f"Report saved to:\n{filepath}")
