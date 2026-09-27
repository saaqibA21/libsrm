"""
Books management screen — catalog, search, add, edit, delete, barcode print
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QDialogButtonBox, QComboBox,
    QMessageBox, QFileDialog, QFrame, QProgressDialog, QApplication
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QColor

from ..database import (add_book, update_book, delete_book,
                        get_all_books, search_books, get_book_by_id)
from ..utils.styles import PRIMARY, DANGER, SUCCESS, WARNING, ACCENT, BG_CARD, TEXT_SECONDARY, BORDER
from ..utils.barcode_utils import generate_barcode_pdf
from ..utils.excel_importer import import_books_from_excel
from .. import database as db


class BookDialog(QDialog):
    """Add / Edit book dialog."""
    def __init__(self, parent=None, book=None):
        super().__init__(parent)
        self.book = book
        self.setWindowTitle("Edit Book" if book else "Add New Book")
        self.setMinimumWidth(480)
        self._build_ui()
        if book:
            self._populate(book)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.barcode_edit = QLineEdit()
        self.barcode_edit.setPlaceholderText("e.g. BK131853")
        if self.book:
            self.barcode_edit.setReadOnly(True)
            self.barcode_edit.setStyleSheet("opacity: 0.7;")

        self.accnum_edit = QLineEdit()
        self.accnum_edit.setPlaceholderText("e.g. 131853 or SRM101")
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Book title")
        self.publisher_edit = QLineEdit()
        self.authors_edit = QLineEdit()
        self.authors_edit.setPlaceholderText("Comma-separated")
        self.edition_edit = QLineEdit()
        self.edition_edit.setPlaceholderText("e.g. 3rd or NIL")

        form.addRow("Barcode *", self.barcode_edit)
        form.addRow("Account No.", self.accnum_edit)
        form.addRow("Title *", self.title_edit)
        form.addRow("Publisher", self.publisher_edit)
        form.addRow("Authors", self.authors_edit)
        form.addRow("Edition", self.edition_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate(self, book):
        self.barcode_edit.setText(book.get("barcode", ""))
        self.accnum_edit.setText(book.get("account_number", ""))
        self.title_edit.setText(book.get("title", ""))
        self.publisher_edit.setText(book.get("publisher", ""))
        self.authors_edit.setText(book.get("authors", ""))
        self.edition_edit.setText(book.get("edition", ""))

    def _validate_and_accept(self):
        if not self.barcode_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Barcode is required.")
            return
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Title is required.")
            return
        self.accept()

    def get_data(self):
        return {
            "barcode": self.barcode_edit.text().strip(),
            "account_number": self.accnum_edit.text().strip(),
            "title": self.title_edit.text().strip(),
            "publisher": self.publisher_edit.text().strip(),
            "authors": self.authors_edit.text().strip(),
            "edition": self.edition_edit.text().strip(),
        }


class BooksScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_books = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header
        header = QHBoxLayout()
        title = QLabel("📚 Books Catalog")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.count_lbl = QLabel("")
        self.count_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.count_lbl)
        layout.addLayout(header)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search by title, author, barcode…")
        self.search_input.setMinimumHeight(36)
        self.search_input.textChanged.connect(self._on_search)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Available", "Issued"])
        self.status_filter.setMinimumHeight(36)
        self.status_filter.currentTextChanged.connect(self._on_search)

        btn_add = QPushButton("➕ Add Book")
        btn_add.setObjectName("btn_success")
        btn_add.setMinimumHeight(36)
        btn_add.clicked.connect(self._add_book)

        btn_import = QPushButton("📥 Import Excel")
        btn_import.setMinimumHeight(36)
        btn_import.clicked.connect(self._import_excel)

        btn_barcode = QPushButton("🏷️ Print Barcodes")
        btn_barcode.setMinimumHeight(36)
        btn_barcode.clicked.connect(self._print_barcodes)

        btn_refresh = QPushButton("🔄")
        btn_refresh.setObjectName("btn_secondary")
        btn_refresh.setMinimumHeight(36)
        btn_refresh.setMaximumWidth(40)
        btn_refresh.clicked.connect(self.refresh)

        toolbar.addWidget(self.search_input, 3)
        toolbar.addWidget(self.status_filter)
        toolbar.addWidget(btn_add)
        toolbar.addWidget(btn_import)
        toolbar.addWidget(btn_barcode)
        toolbar.addWidget(btn_refresh)
        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Barcode", "Account No.", "Title", "Authors", "Publisher", "Edition", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.table.doubleClicked.connect(self._edit_selected)
        layout.addWidget(self.table)

        # Bottom actions
        bottom = QHBoxLayout()
        btn_edit = QPushButton("✏️ Edit")
        btn_edit.setObjectName("btn_secondary")
        btn_edit.clicked.connect(self._edit_selected)

        btn_del = QPushButton("🗑️ Delete")
        btn_del.setObjectName("btn_danger")
        btn_del.clicked.connect(self._delete_selected)

        self.sel_lbl = QLabel("Select a book to edit or delete")
        self.sel_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")

        bottom.addWidget(self.sel_lbl)
        bottom.addStretch()
        bottom.addWidget(btn_edit)
        bottom.addWidget(btn_del)
        layout.addLayout(bottom)

    def refresh(self):
        self._all_books = get_all_books()
        self._populate_table(self._all_books)
        counts = db.count_books()
        self.count_lbl.setText(f"Total: {counts['total']}  •  Available: {counts['available']}  •  Issued: {counts['issued']}")

    def _on_search(self):
        q = self.search_input.text().strip()
        sf = self.status_filter.currentText().lower()
        status = None if sf == "all" else sf
        results = search_books(q, status)
        self._populate_table(results)

    def _populate_table(self, books):
        self.table.setRowCount(0)
        for book in books:
            row = self.table.rowCount()
            self.table.insertRow(row)
            status = book.get("status", "available")
            color = SUCCESS if status == "available" else DANGER

            vals = [
                book.get("barcode", ""),
                book.get("account_number", ""),
                book.get("title", ""),
                (book.get("authors", "") or "")[:50],
                (book.get("publisher", "") or "")[:30],
                book.get("edition", "") or "",
                status.upper(),
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                item.setData(Qt.ItemDataRole.UserRole, book["id"])
                if col == 6:
                    item.setForeground(QColor(color))
                    item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                self.table.setItem(row, col, item)

    def _get_selected_book_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _add_book(self):
        dlg = BookDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            success, msg = add_book(**data)
            if success:
                self.refresh()
                QMessageBox.information(self, "Success", msg)
            else:
                QMessageBox.warning(self, "Error", msg)

    def _edit_selected(self):
        book_id = self._get_selected_book_id()
        if not book_id:
            QMessageBox.information(self, "Select", "Please select a book first.")
            return
        book = get_book_by_id(book_id)
        if not book:
            return
        dlg = BookDialog(self, book)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            update_book(book_id, data["title"], data["publisher"],
                        data["authors"], data["edition"], data["account_number"])
            self.refresh()

    def _delete_selected(self):
        book_id = self._get_selected_book_id()
        if not book_id:
            QMessageBox.information(self, "Select", "Please select a book first.")
            return
        book = get_book_by_id(book_id)
        if book and book.get("status") == "issued":
            QMessageBox.warning(self, "Cannot Delete", "Cannot delete a book that is currently issued.")
            return
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Delete book: {book['title']}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            delete_book(book_id)
            self.refresh()

    def _context_menu(self, pos):
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.addAction("✏️ Edit", self._edit_selected)
        menu.addAction("🗑️ Delete", self._delete_selected)
        menu.exec(self.table.mapToGlobal(pos))

    def _import_excel(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Books Excel File",
            str(__import__("pathlib").Path.home()),
            "Excel Files (*.xlsx *.xls)"
        )
        if not filepath:
            return

        books, errors = import_books_from_excel(filepath)
        if not books:
            QMessageBox.warning(self, "Import", f"No books found.\n{chr(10).join(errors)}")
            return

        progress = QProgressDialog(f"Importing {len(books)} books…", "Cancel", 0, len(books), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)

        added = 0
        skipped = 0
        for i, book in enumerate(books):
            progress.setValue(i)
            if progress.wasCanceled():
                break
            QApplication.processEvents()
            success, _ = add_book(**book)
            if success:
                added += 1
            else:
                skipped += 1

        progress.setValue(len(books))
        self.refresh()
        QMessageBox.information(
            self, "Import Complete",
            f"✅ Imported: {added} books\n⚠️ Skipped (duplicates): {skipped}"
        )

    def _print_barcodes(self):
        books = get_all_books()
        if not books:
            QMessageBox.information(self, "No Books", "No books in catalog.")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Barcode PDF", "book_barcodes.pdf", "PDF Files (*.pdf)"
        )
        if not filepath:
            return

        items = [
            {
                "barcode": b["barcode"],
                "name": b["title"][:50],
                "extra": f"Acc: {b.get('account_number', '')}  |  {b.get('authors', '')[:35]}",
            }
            for b in books
        ]

        try:
            generate_barcode_pdf(items, filepath, label_type="book")
            QMessageBox.information(self, "Done", f"Barcode PDF saved to:\n{filepath}")
            import subprocess
            subprocess.Popen(["start", "", filepath], shell=True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not generate PDF:\n{e}")
