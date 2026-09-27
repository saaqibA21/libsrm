"""
Patrons management screen — students & teachers
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QDialogButtonBox, QComboBox,
    QMessageBox, QFileDialog, QApplication, QProgressDialog, QTabWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from ..database import (add_patron, update_patron, delete_patron,
                        get_all_patrons, search_patrons, get_patron_by_id,
                        get_patron_history, count_patrons)
from ..utils.styles import PRIMARY, DANGER, SUCCESS, WARNING, ACCENT, TEXT_SECONDARY, BG_CARD
from ..utils.barcode_utils import generate_barcode_pdf
from ..utils.excel_importer import import_students_from_excel, import_staff_from_excel


class PatronDialog(QDialog):
    """Add / Edit patron dialog."""
    def __init__(self, parent=None, patron=None):
        super().__init__(parent)
        self.patron = patron
        self.setWindowTitle("Edit Patron" if patron else "Add New Patron")
        self.setMinimumWidth(500)
        self._build_ui()
        if patron:
            self._populate(patron)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.barcode_edit = QLineEdit()
        self.barcode_edit.setPlaceholderText("e.g. STRA2611005010001")
        if self.patron:
            self.barcode_edit.setReadOnly(True)

        self.reg_edit = QLineEdit()
        self.reg_edit.setPlaceholderText("Register/Employee number")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Full name")

        self.type_combo = QComboBox()
        self.type_combo.addItems(["student", "teacher"])

        self.year_combo = QComboBox()
        self.year_combo.addItems(["", "I", "II", "III", "IV"])

        self.section_edit = QLineEdit()
        self.section_edit.setPlaceholderText("A / B / C / D")

        self.mobile_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.parent_mobile_edit = QLineEdit()
        self.parent_email_edit = QLineEdit()

        form.addRow("Barcode *", self.barcode_edit)
        form.addRow("Reg. Number *", self.reg_edit)
        form.addRow("Name *", self.name_edit)
        form.addRow("Type", self.type_combo)
        form.addRow("Year", self.year_combo)
        form.addRow("Section", self.section_edit)
        form.addRow("Mobile", self.mobile_edit)
        form.addRow("Email", self.email_edit)
        form.addRow("Parent Mobile", self.parent_mobile_edit)
        form.addRow("Parent Email", self.parent_email_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate(self, p):
        self.barcode_edit.setText(p.get("barcode", ""))
        self.reg_edit.setText(p.get("register_number", ""))
        self.name_edit.setText(p.get("name", ""))
        idx = self.type_combo.findText(p.get("patron_type", "student"))
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        idx2 = self.year_combo.findText(p.get("year", ""))
        if idx2 >= 0:
            self.year_combo.setCurrentIndex(idx2)
        self.section_edit.setText(p.get("section", ""))
        self.mobile_edit.setText(p.get("mobile", ""))
        self.email_edit.setText(p.get("email", ""))
        self.parent_mobile_edit.setText(p.get("parent_mobile", ""))
        self.parent_email_edit.setText(p.get("parent_email", ""))

    def _validate_and_accept(self):
        if not self.barcode_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Barcode is required.")
            return
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Name is required.")
            return
        self.accept()

    def get_data(self):
        return {
            "barcode": self.barcode_edit.text().strip(),
            "register_number": self.reg_edit.text().strip(),
            "name": self.name_edit.text().strip(),
            "patron_type": self.type_combo.currentText(),
            "year": self.year_combo.currentText(),
            "section": self.section_edit.text().strip(),
            "mobile": self.mobile_edit.text().strip(),
            "email": self.email_edit.text().strip(),
            "parent_mobile": self.parent_mobile_edit.text().strip(),
            "parent_email": self.parent_email_edit.text().strip(),
        }


class ImportStudentsDialog(QDialog):
    """Dialog to select Excel file and enter year/section for import."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Students from Excel")
        self.setMinimumWidth(440)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        self.file_edit.setPlaceholderText("Click Browse to select file…")
        btn_browse = QPushButton("Browse…")
        btn_browse.clicked.connect(self._browse)

        file_row = QHBoxLayout()
        file_row.addWidget(self.file_edit)
        file_row.addWidget(btn_browse)
        form.addRow("Excel File *", file_row)

        self.year_combo = QComboBox()
        self.year_combo.addItems(["I", "II", "III", "IV"])
        form.addRow("Year", self.year_combo)

        self.section_edit = QLineEdit()
        self.section_edit.setPlaceholderText("e.g. A")
        form.addRow("Section", self.section_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Student Excel File", "",
            "Excel Files (*.xlsx *.xls)"
        )
        if filepath:
            self.file_edit.setText(filepath)

    def _validate_and_accept(self):
        if not self.file_edit.text():
            QMessageBox.warning(self, "Validation", "Please select a file.")
            return
        self.accept()

    def get_data(self):
        return {
            "filepath": self.file_edit.text(),
            "year": self.year_combo.currentText(),
            "section": self.section_edit.text().strip().upper() or "?",
        }


class PatronsScreen(QWidget):
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
        title = QLabel("👥 Patrons")
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
        self.search_input.setPlaceholderText("🔍 Search by name, reg. no., barcode…")
        self.search_input.setMinimumHeight(36)
        self.search_input.textChanged.connect(self._on_search)

        self.type_filter = QComboBox()
        self.type_filter.addItems(["All", "Students", "Teachers"])
        self.type_filter.setMinimumHeight(36)
        self.type_filter.currentTextChanged.connect(self._on_search)

        btn_add = QPushButton("➕ Add Patron")
        btn_add.setObjectName("btn_success")
        btn_add.setMinimumHeight(36)
        btn_add.clicked.connect(self._add_patron)

        btn_import_students = QPushButton("📥 Import Students")
        btn_import_students.setMinimumHeight(36)
        btn_import_students.clicked.connect(self._import_students)

        btn_import_staff = QPushButton("📥 Import Staff")
        btn_import_staff.setMinimumHeight(36)
        btn_import_staff.clicked.connect(self._import_staff)

        btn_barcode = QPushButton("🏷️ Print ID Cards")
        btn_barcode.setMinimumHeight(36)
        btn_barcode.clicked.connect(self._print_barcodes)

        btn_refresh = QPushButton("🔄")
        btn_refresh.setObjectName("btn_secondary")
        btn_refresh.setMinimumHeight(36)
        btn_refresh.setMaximumWidth(40)
        btn_refresh.clicked.connect(self.refresh)

        toolbar.addWidget(self.search_input, 3)
        toolbar.addWidget(self.type_filter)
        toolbar.addWidget(btn_add)
        toolbar.addWidget(btn_import_students)
        toolbar.addWidget(btn_import_staff)
        toolbar.addWidget(btn_barcode)
        toolbar.addWidget(btn_refresh)
        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["Barcode", "Reg. No.", "Name", "Type", "Year", "Section", "Mobile", "Email"]
        )
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.doubleClicked.connect(self._edit_selected)
        layout.addWidget(self.table)

        # Bottom actions
        bottom = QHBoxLayout()
        btn_view = QPushButton("📋 View History")
        btn_view.setObjectName("btn_secondary")
        btn_view.clicked.connect(self._view_history)

        btn_edit = QPushButton("✏️ Edit")
        btn_edit.setObjectName("btn_secondary")
        btn_edit.clicked.connect(self._edit_selected)

        btn_del = QPushButton("🗑️ Delete")
        btn_del.setObjectName("btn_danger")
        btn_del.clicked.connect(self._delete_selected)

        bottom.addStretch()
        bottom.addWidget(btn_view)
        bottom.addWidget(btn_edit)
        bottom.addWidget(btn_del)
        layout.addLayout(bottom)

    def refresh(self):
        patrons = get_all_patrons()
        self._populate_table(patrons)
        counts = count_patrons()
        self.count_lbl.setText(
            f"Total: {counts['total']}  •  Students: {counts['students']}  •  Teachers: {counts['teachers']}"
        )

    def _on_search(self):
        q = self.search_input.text().strip()
        tf = self.type_filter.currentText().lower()
        pt = None if tf == "all" else ("teacher" if tf == "teachers" else "student")
        results = search_patrons(q, pt)
        self._populate_table(results)

    def _populate_table(self, patrons):
        self.table.setRowCount(0)
        for p in patrons:
            row = self.table.rowCount()
            self.table.insertRow(row)
            color = ACCENT if p.get("patron_type") == "teacher" else TEXT_SECONDARY
            vals = [
                p.get("barcode", ""),
                p.get("register_number", ""),
                p.get("name", ""),
                p.get("patron_type", "").title(),
                p.get("year", ""),
                p.get("section", ""),
                p.get("mobile", ""),
                p.get("email", ""),
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                item.setData(Qt.ItemDataRole.UserRole, p["id"])
                if col == 3:
                    item.setForeground(QColor(color))
                    item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                self.table.setItem(row, col, item)

    def _get_selected_patron_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _add_patron(self):
        dlg = PatronDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            success, msg = add_patron(**data)
            if success:
                self.refresh()
                QMessageBox.information(self, "Success", msg)
            else:
                QMessageBox.warning(self, "Error", msg)

    def _edit_selected(self):
        pid = self._get_selected_patron_id()
        if not pid:
            QMessageBox.information(self, "Select", "Please select a patron first.")
            return
        patron = get_patron_by_id(pid)
        dlg = PatronDialog(self, patron)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            update_patron(pid, data["name"], data["patron_type"], data["year"],
                          data["section"], data["mobile"], data["email"],
                          data["parent_mobile"], data["parent_email"])
            self.refresh()

    def _delete_selected(self):
        pid = self._get_selected_patron_id()
        if not pid:
            QMessageBox.information(self, "Select", "Please select a patron first.")
            return
        patron = get_patron_by_id(pid)
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete patron: {patron['name']}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_patron(pid)
            self.refresh()

    def _view_history(self):
        pid = self._get_selected_patron_id()
        if not pid:
            QMessageBox.information(self, "Select", "Please select a patron first.")
            return
        patron = get_patron_by_id(pid)
        history = get_patron_history(pid)

        dlg = QDialog(self)
        dlg.setWindowTitle(f"History — {patron['name']}")
        dlg.setMinimumSize(700, 400)
        layout = QVBoxLayout(dlg)

        lbl = QLabel(f"📋 Borrowing History: {patron['name']} ({patron.get('register_number','')})")
        lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        layout.addWidget(lbl)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Book", "Issue Date", "Due Date", "Return Date", "Fine"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)

        for txn in history:
            row = table.rowCount()
            table.insertRow(row)
            vals = [
                txn.get("book_title", ""),
                txn.get("issue_date", ""),
                txn.get("due_date", ""),
                txn.get("return_date", "") or "—",
                f"₹{txn.get('fine_amount', 0):.2f}" if txn.get("fine_amount") else "₹0",
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                if txn.get("status") == "issued":
                    item.setForeground(QColor(ACCENT))
                table.setItem(row, col, item)

        layout.addWidget(table)
        dlg.exec()

    def _import_students(self):
        dlg = ImportStudentsDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()
        patrons, errors = import_students_from_excel(data["filepath"], data["year"], data["section"])

        if not patrons:
            QMessageBox.warning(self, "Import", f"No students found.\n{chr(10).join(errors)}")
            return

        progress = QProgressDialog(f"Importing {len(patrons)} students…", "Cancel", 0, len(patrons), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)

        added = skipped = 0
        for i, p in enumerate(patrons):
            progress.setValue(i)
            if progress.wasCanceled():
                break
            QApplication.processEvents()
            success, _ = add_patron(**p)
            if success:
                added += 1
            else:
                skipped += 1

        progress.setValue(len(patrons))
        self.refresh()
        QMessageBox.information(self, "Import Complete",
                                f"✅ Imported: {added}\n⚠️ Skipped (duplicates): {skipped}")

    def _import_staff(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Staff Excel File", "",
            "Excel Files (*.xlsx *.xls)"
        )
        if not filepath:
            return

        patrons, errors = import_staff_from_excel(filepath)
        if not patrons:
            QMessageBox.warning(self, "Import", f"No staff found.\n{chr(10).join(errors)}")
            return

        added = skipped = 0
        for p in patrons:
            success, _ = add_patron(**p)
            if success:
                added += 1
            else:
                skipped += 1

        self.refresh()
        QMessageBox.information(self, "Import Complete",
                                f"✅ Imported: {added}\n⚠️ Skipped: {skipped}")

    def _print_barcodes(self):
        patrons = get_all_patrons()
        if not patrons:
            QMessageBox.information(self, "No Patrons", "No patrons registered.")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save ID Card PDF", "patron_barcodes.pdf", "PDF Files (*.pdf)"
        )
        if not filepath:
            return

        items = [
            {
                "barcode": p["barcode"],
                "name": p["name"],
                "extra": f"{p.get('patron_type','').title()} | {p.get('register_number','')} | Sec {p.get('section','')}",
            }
            for p in patrons
        ]
        try:
            generate_barcode_pdf(items, filepath, label_type="patron")
            QMessageBox.information(self, "Done", f"ID Card PDF saved to:\n{filepath}")
            import subprocess
            subprocess.Popen(["start", "", filepath], shell=True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not generate PDF:\n{e}")
