"""
Issue & Return screen — barcode scan workflow
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QGroupBox, QFormLayout,
    QSizePolicy, QTextEdit
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QColor, QKeyEvent

from datetime import datetime

from ..database import (
    get_book_by_barcode, get_patron_by_barcode,
    get_active_transaction_by_book, get_patron_active_books,
    issue_book, return_book, get_setting
)
from ..utils.styles import (PRIMARY, DANGER, WARNING, SUCCESS, ACCENT,
                             BG_CARD, BG_INPUT, TEXT_PRIMARY, TEXT_SECONDARY, BORDER)


class BarcodeInput(QLineEdit):
    """Custom QLineEdit that triggers on Enter or barcode scanner completion."""
    barcode_entered = Signal(str)

    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.returnPressed.connect(self._on_enter)
        self.setMinimumHeight(48)
        self.setFont(QFont("Consolas", 15))
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._on_enter)

    def keyPressEvent(self, event: QKeyEvent):
        super().keyPressEvent(event)
        # Barcode scanners send chars rapidly then Enter; this handles both
        if event.key() not in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._timer.start()

    def _on_enter(self):
        text = self.text().strip()
        if text:
            self.barcode_entered.emit(text)


def make_info_row(label_text, value_text="—", highlight=False):
    hl = QHBoxLayout()
    lbl = QLabel(label_text + ":")
    lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px; min-width: 110px;")
    val = QLabel(str(value_text))
    val.setWordWrap(True)
    if highlight:
        val.setStyleSheet(f"color: {ACCENT}; font-weight: 700; font-size: 14px;")
    else:
        val.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px;")
    hl.addWidget(lbl)
    hl.addWidget(val)
    hl.addStretch()
    return hl, val


class IssueReturnScreen(QWidget):
    book_issued = Signal()
    book_returned = Signal()

    def __init__(self, mode="issue", parent=None):
        """mode: 'issue' or 'return'"""
        super().__init__(parent)
        self.mode = mode
        self._book_data = None
        self._patron_data = None
        self._active_txn = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Title
        if self.mode == "issue":
            title_text = "📤 Issue Book"
            title_color = SUCCESS
        else:
            title_text = "📥 Return Book"
            title_color = WARNING

        title = QLabel(title_text)
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {title_color};")
        layout.addWidget(title)

        subtitle = QLabel(
            "Scan the book barcode first, then scan the patron barcode to complete the transaction."
            if self.mode == "issue" else
            "Scan the book barcode to look up the active loan and process the return."
        )
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # Main content
        content = QHBoxLayout()
        content.setSpacing(16)

        # ─── Left: Scan Panel ─────────────────────────────────────────────
        scan_frame = QFrame()
        scan_frame.setObjectName("card")
        scan_frame.setMaximumWidth(380)
        scan_layout = QVBoxLayout(scan_frame)
        scan_layout.setContentsMargins(18, 16, 18, 16)
        scan_layout.setSpacing(14)

        # Step 1: Book scan
        step1_grp = QGroupBox("Step 1 — Scan Book Barcode")
        step1_layout = QVBoxLayout(step1_grp)
        self.book_input = BarcodeInput("📚 Scan or type book barcode…")
        self.book_input.barcode_entered.connect(self._on_book_scanned)
        step1_layout.addWidget(self.book_input)

        self.book_status_lbl = QLabel("")
        self.book_status_lbl.setWordWrap(True)
        self.book_status_lbl.setMinimumHeight(18)
        step1_layout.addWidget(self.book_status_lbl)
        scan_layout.addWidget(step1_grp)

        # Step 2: Patron scan (only for issue)
        if self.mode == "issue":
            step2_grp = QGroupBox("Step 2 — Scan Patron Barcode")
            step2_layout = QVBoxLayout(step2_grp)
            self.patron_input = BarcodeInput("👤 Scan or type patron barcode…")
            self.patron_input.barcode_entered.connect(self._on_patron_scanned)
            self.patron_input.setEnabled(False)
            step2_layout.addWidget(self.patron_input)

            self.patron_status_lbl = QLabel("")
            self.patron_status_lbl.setWordWrap(True)
            self.patron_status_lbl.setMinimumHeight(18)
            step2_layout.addWidget(self.patron_status_lbl)
            scan_layout.addWidget(step2_grp)

        # Action button
        if self.mode == "issue":
            self.action_btn = QPushButton("📤  ISSUE BOOK")
            self.action_btn.setObjectName("btn_success")
        else:
            self.action_btn = QPushButton("📥  RETURN BOOK")
            self.action_btn.setObjectName("btn_warning")

        self.action_btn.setMinimumHeight(50)
        self.action_btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.action_btn.setEnabled(False)
        self.action_btn.clicked.connect(self._on_action)
        scan_layout.addWidget(self.action_btn)

        # Clear button
        btn_clear = QPushButton("🔄  Clear / New Transaction")
        btn_clear.setObjectName("btn_secondary")
        btn_clear.clicked.connect(self.clear)
        scan_layout.addWidget(btn_clear)

        scan_layout.addStretch()
        content.addWidget(scan_frame)

        # ─── Right: Info Panel ────────────────────────────────────────────
        right_layout = QVBoxLayout()
        right_layout.setSpacing(14)

        # Book details card
        self.book_card = QFrame()
        self.book_card.setObjectName("card")
        book_card_layout = QVBoxLayout(self.book_card)
        book_card_layout.setContentsMargins(16, 14, 16, 14)
        book_title_header = QLabel("📚 Book Details")
        book_title_header.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        book_card_layout.addWidget(book_title_header)

        self.book_detail_rows = {}
        for field in ["Title", "Account No.", "Authors", "Publisher", "Edition", "Status"]:
            row, val = make_info_row(field, "—", field == "Status")
            self.book_detail_rows[field] = val
            book_card_layout.addLayout(row)
        right_layout.addWidget(self.book_card)

        # Patron details card
        self.patron_card = QFrame()
        self.patron_card.setObjectName("card")
        patron_card_layout = QVBoxLayout(self.patron_card)
        patron_card_layout.setContentsMargins(16, 14, 16, 14)
        patron_title_header = QLabel("👤 Patron Details")
        patron_title_header.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        patron_card_layout.addWidget(patron_title_header)

        self.patron_detail_rows = {}
        for field in ["Name", "Reg. No.", "Type", "Year/Section", "Mobile", "Email", "Books Held"]:
            row, val = make_info_row(field, "—", field == "Type")
            self.patron_detail_rows[field] = val
            patron_card_layout.addLayout(row)

        # Active books table for patron
        self.active_books_lbl = QLabel("📋 Currently Issued Books")
        self.active_books_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.active_books_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; margin-top: 8px;")
        patron_card_layout.addWidget(self.active_books_lbl)

        self.active_books_table = QTableWidget()
        self.active_books_table.setColumnCount(3)
        self.active_books_table.setHorizontalHeaderLabels(["Book Title", "Issue Date", "Due Date"])
        self.active_books_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.active_books_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.active_books_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.active_books_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.active_books_table.verticalHeader().setVisible(False)
        self.active_books_table.setMaximumHeight(150)
        patron_card_layout.addWidget(self.active_books_table)
        right_layout.addWidget(self.patron_card)

        # Transaction result card
        self.result_card = QFrame()
        self.result_card.setObjectName("card")
        self.result_card.setVisible(False)
        result_layout = QVBoxLayout(self.result_card)
        result_layout.setContentsMargins(16, 14, 16, 14)
        self.result_lbl = QLabel("")
        self.result_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.result_lbl.setWordWrap(True)
        self.result_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        result_layout.addWidget(self.result_lbl)
        self.fine_lbl = QLabel("")
        self.fine_lbl.setFont(QFont("Segoe UI", 12))
        self.fine_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.fine_lbl.setWordWrap(True)
        result_layout.addWidget(self.fine_lbl)
        right_layout.addWidget(self.result_card)

        right_layout.addStretch()
        content.addLayout(right_layout, 1)
        layout.addLayout(content)

    def _set_status(self, label, text, color=SUCCESS):
        label.setText(text)
        label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 600;")

    def _on_book_scanned(self, barcode):
        self._book_data = None
        self._active_txn = None
        barcode = barcode.strip()

        book = get_book_by_barcode(barcode)
        if not book:
            self._set_status(self.book_status_lbl, f"❌ Book '{barcode}' not found!", DANGER)
            self._clear_book_details()
            return

        self._book_data = book
        self._populate_book_details(book)

        if self.mode == "issue":
            if book["status"] != "available":
                self._set_status(self.book_status_lbl,
                                 "⚠️ This book is currently issued to someone else!", WARNING)
                self.patron_input.setEnabled(False)
            else:
                self._set_status(self.book_status_lbl, "✅ Book found — now scan patron barcode", SUCCESS)
                self.patron_input.setEnabled(True)
                self.patron_input.setFocus()
        else:  # return
            txn = get_active_transaction_by_book(book["id"])
            if not txn:
                self._set_status(self.book_status_lbl, "⚠️ No active loan found for this book", WARNING)
            else:
                self._active_txn = txn
                self._set_status(self.book_status_lbl,
                                 f"✅ Active loan found — issued to: {txn['patron_name']}", SUCCESS)
                self._populate_patron_from_txn(txn)
                self.action_btn.setEnabled(True)

    def _on_patron_scanned(self, barcode):
        self._patron_data = None
        barcode = barcode.strip()

        patron = get_patron_by_barcode(barcode)
        if not patron:
            self._set_status(self.patron_status_lbl, f"❌ Patron '{barcode}' not found!", DANGER)
            self._clear_patron_details()
            return

        self._patron_data = patron
        self._populate_patron_details(patron)
        self._set_status(self.patron_status_lbl, f"✅ Patron found: {patron['name']}", SUCCESS)

        if self._book_data and self._book_data["status"] == "available":
            self.action_btn.setEnabled(True)

    def _populate_book_details(self, book):
        self.book_detail_rows["Title"].setText(book.get("title", "—"))
        self.book_detail_rows["Account No."].setText(book.get("account_number", "—"))
        self.book_detail_rows["Authors"].setText(book.get("authors", "—") or "—")
        self.book_detail_rows["Publisher"].setText(book.get("publisher", "—") or "—")
        self.book_detail_rows["Edition"].setText(book.get("edition", "—") or "—")
        status = book.get("status", "—")
        color = SUCCESS if status == "available" else DANGER
        self.book_detail_rows["Status"].setText(status.upper())
        self.book_detail_rows["Status"].setStyleSheet(f"color: {color}; font-weight: 700; font-size: 14px;")

    def _clear_book_details(self):
        for lbl in self.book_detail_rows.values():
            lbl.setText("—")

    def _populate_patron_details(self, patron):
        self.patron_detail_rows["Name"].setText(patron.get("name", "—"))
        self.patron_detail_rows["Reg. No."].setText(patron.get("register_number", "—"))
        self.patron_detail_rows["Type"].setText(patron.get("patron_type", "—").title())
        year_sec = f"Year {patron.get('year', '')} — Section {patron.get('section', '')}"
        self.patron_detail_rows["Year/Section"].setText(year_sec if patron.get("year") else "—")
        self.patron_detail_rows["Mobile"].setText(patron.get("mobile", "—"))
        self.patron_detail_rows["Email"].setText(patron.get("email", "—"))

        # Load active books
        active = get_patron_active_books(patron["id"])
        self.patron_detail_rows["Books Held"].setText(str(len(active)))
        self.active_books_table.setRowCount(0)
        today = datetime.now().strftime("%Y-%m-%d")
        for txn in active:
            row = self.active_books_table.rowCount()
            self.active_books_table.insertRow(row)
            due = txn.get("due_date", "")
            overdue = due < today
            items = [txn.get("book_title", "")[:45], txn.get("issue_date", ""), due]
            for col, text in enumerate(items):
                item = QTableWidgetItem(str(text))
                if overdue:
                    item.setForeground(QColor(DANGER))
                self.active_books_table.setItem(row, col, item)

    def _populate_patron_from_txn(self, txn):
        self.patron_detail_rows["Name"].setText(txn.get("patron_name", "—"))
        self.patron_detail_rows["Reg. No."].setText(txn.get("register_number", "—"))
        self.patron_detail_rows["Type"].setText(txn.get("patron_type", "—").title())
        self.patron_detail_rows["Email"].setText(txn.get("patron_email", "—"))
        # Show issue info
        self.patron_detail_rows["Year/Section"].setText(
            f"Issued: {txn.get('issue_date', '—')}  |  Due: {txn.get('due_date', '—')}"
        )
        due = txn.get("due_date", "")
        today = datetime.now().strftime("%Y-%m-%d")
        if due < today:
            overdue_days = (datetime.now() - datetime.strptime(due, "%Y-%m-%d")).days
            fine_rate = float(get_setting("fine_per_day", "2.0"))
            fine = overdue_days * fine_rate
            self.patron_detail_rows["Mobile"].setText(
                f"⚠️ OVERDUE by {overdue_days} days — Fine: ₹{fine:.2f}"
            )
            self.patron_detail_rows["Mobile"].setStyleSheet(f"color: {DANGER}; font-weight: 700;")

    def _clear_patron_details(self):
        for lbl in self.patron_detail_rows.values():
            lbl.setText("—")
        self.active_books_table.setRowCount(0)

    def _on_action(self):
        if self.mode == "issue":
            if not self._book_data or not self._patron_data:
                return
            success, msg = issue_book(
                self._book_data["id"],
                self._patron_data["id"],
                self._patron_data.get("patron_type", "student")
            )
            if success:
                self._show_result(
                    f"✅ Book Issued Successfully!\n{self._book_data['title']}",
                    f"📅 {msg}\n👤 Issued to: {self._patron_data['name']}",
                    SUCCESS
                )
                self.book_issued.emit()
                QTimer.singleShot(3000, self.clear)
            else:
                QMessageBox.warning(self, "Issue Failed", msg)

        else:  # return
            if not self._active_txn:
                return
            success, result = return_book(self._active_txn["id"])
            if success:
                fine = float(result)
                fine_msg = f"💰 Fine: ₹{fine:.2f}" if fine > 0 else "✅ No fine — returned on time!"
                self._show_result(
                    f"✅ Book Returned Successfully!\n{self._book_data['title']}",
                    fine_msg,
                    SUCCESS if fine == 0 else WARNING
                )
                self.book_returned.emit()
                QTimer.singleShot(3000, self.clear)
            else:
                QMessageBox.warning(self, "Return Failed", str(result))

    def _show_result(self, title, body, color):
        self.result_card.setVisible(True)
        self.result_lbl.setText(title)
        self.result_lbl.setStyleSheet(f"color: {color}; font-weight: 700; font-size: 14px;")
        self.fine_lbl.setText(body)
        self.fine_lbl.setStyleSheet(f"color: {color}; font-size: 13px;")
        self.action_btn.setEnabled(False)

    def clear(self):
        self.book_input.clear()
        self.book_input.setFocus()
        if self.mode == "issue":
            self.patron_input.clear()
            self.patron_input.setEnabled(False)
            self.patron_status_lbl.setText("")
        self.book_status_lbl.setText("")
        self._book_data = None
        self._patron_data = None
        self._active_txn = None
        self._clear_book_details()
        self._clear_patron_details()
        self.action_btn.setEnabled(False)
        self.result_card.setVisible(False)

    def focus_book_input(self):
        self.clear()
        self.book_input.setFocus()
