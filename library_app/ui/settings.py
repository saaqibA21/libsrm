"""
Settings screen — configure loan periods, fines, email, library info
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFormLayout, QGroupBox, QSpinBox, QDoubleSpinBox,
    QMessageBox, QTabWidget, QCheckBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ..database import get_all_settings, set_setting
from ..utils.styles import TEXT_SECONDARY, SUCCESS, WARNING
from ..utils.email_utils import send_email


class SettingsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("⚙️ Settings")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        layout.addWidget(title)

        tabs = QTabWidget()

        # ─── Library Tab ────────────────────────────────────────────────────────
        lib_widget = QWidget()
        lib_layout = QVBoxLayout(lib_widget)
        lib_layout.setContentsMargins(20, 20, 20, 20)

        lib_grp = QGroupBox("Library Information")
        lib_form = QFormLayout(lib_grp)
        lib_form.setSpacing(12)
        lib_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.lib_name_edit = QLineEdit()
        self.lib_name_edit.setPlaceholderText("Library name shown in emails and reports")
        lib_form.addRow("Library Name", self.lib_name_edit)

        lib_layout.addWidget(lib_grp)

        # Loan & Fine settings
        loan_grp = QGroupBox("Loan Period & Fines")
        loan_form = QFormLayout(loan_grp)
        loan_form.setSpacing(12)
        loan_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.student_loan_spin = QSpinBox()
        self.student_loan_spin.setRange(1, 365)
        self.student_loan_spin.setSuffix(" days")
        loan_form.addRow("Student Loan Period", self.student_loan_spin)

        self.teacher_loan_spin = QSpinBox()
        self.teacher_loan_spin.setRange(1, 365)
        self.teacher_loan_spin.setSuffix(" days")
        loan_form.addRow("Teacher Loan Period", self.teacher_loan_spin)

        self.fine_spin = QDoubleSpinBox()
        self.fine_spin.setRange(0, 100)
        self.fine_spin.setSingleStep(0.5)
        self.fine_spin.setPrefix("₹ ")
        self.fine_spin.setSuffix(" per day")
        loan_form.addRow("Fine Rate", self.fine_spin)

        lib_layout.addWidget(loan_grp)
        lib_layout.addStretch()

        btn_save_lib = QPushButton("💾 Save Library Settings")
        btn_save_lib.setObjectName("btn_success")
        btn_save_lib.setMinimumHeight(40)
        btn_save_lib.clicked.connect(self._save_library_settings)
        lib_layout.addWidget(btn_save_lib)

        tabs.addTab(lib_widget, "📚 Library")

        # ─── Email Tab ──────────────────────────────────────────────────────────
        email_widget = QWidget()
        email_layout = QVBoxLayout(email_widget)
        email_layout.setContentsMargins(20, 20, 20, 20)

        email_grp = QGroupBox("Email / SMTP Configuration")
        email_grp.setToolTip("For Gmail: use your email, enable 2FA, and use an App Password")
        email_form = QFormLayout(email_grp)
        email_form.setSpacing(12)
        email_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.smtp_host_edit = QLineEdit()
        self.smtp_host_edit.setPlaceholderText("smtp.gmail.com")
        email_form.addRow("SMTP Host", self.smtp_host_edit)

        self.smtp_port_spin = QSpinBox()
        self.smtp_port_spin.setRange(1, 65535)
        self.smtp_port_spin.setValue(587)
        email_form.addRow("SMTP Port", self.smtp_port_spin)

        self.email_user_edit = QLineEdit()
        self.email_user_edit.setPlaceholderText("your@gmail.com")
        email_form.addRow("Email Address", self.email_user_edit)

        self.email_pass_edit = QLineEdit()
        self.email_pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.email_pass_edit.setPlaceholderText("App password (not your main password)")
        email_form.addRow("App Password", self.email_pass_edit)

        self.email_from_edit = QLineEdit()
        self.email_from_edit.setPlaceholderText("Leave blank to use email address above")
        email_form.addRow("From Address", self.email_from_edit)

        email_layout.addWidget(email_grp)

        hint = QLabel(
            "💡 For Gmail: Go to Google Account → Security → 2-Step Verification (enable it) → "
            "App passwords → Generate one and paste it above."
        )
        hint.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        hint.setWordWrap(True)
        email_layout.addWidget(hint)
        email_layout.addStretch()

        email_btn_row = QHBoxLayout()
        btn_test_email = QPushButton("📧 Send Test Email")
        btn_test_email.setObjectName("btn_secondary")
        btn_test_email.clicked.connect(self._send_test_email)

        btn_save_email = QPushButton("💾 Save Email Settings")
        btn_save_email.setObjectName("btn_success")
        btn_save_email.setMinimumHeight(40)
        btn_save_email.clicked.connect(self._save_email_settings)

        email_btn_row.addWidget(btn_test_email)
        email_btn_row.addStretch()
        email_btn_row.addWidget(btn_save_email)
        email_layout.addLayout(email_btn_row)

        tabs.addTab(email_widget, "📧 Email")

        # ─── About Tab ──────────────────────────────────────────────────────────
        about_widget = QWidget()
        about_layout = QVBoxLayout(about_widget)
        about_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_layout.setContentsMargins(40, 40, 40, 40)

        about_title = QLabel("📚 SRM EEE Library Management System")
        about_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        about_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        about_version = QLabel("Version 1.0  •  Built with Python & PySide6")
        about_version.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")
        about_version.setAlignment(Qt.AlignmentFlag.AlignCenter)

        about_desc = QLabel(
            "A modern barcode-based library management system for\n"
            "SRM EEE Department. Supports students, teaching &\n"
            "non-teaching staff, book issue/return, fines, and email reminders."
        )
        about_desc.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        about_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)

        about_layout.addWidget(about_title)
        about_layout.addSpacing(10)
        about_layout.addWidget(about_version)
        about_layout.addSpacing(16)
        about_layout.addWidget(about_desc)

        tabs.addTab(about_widget, "ℹ️ About")

        layout.addWidget(tabs)

    def _load_settings(self):
        s = get_all_settings()
        self.lib_name_edit.setText(s.get("library_name", "SRM EEE Department Library"))
        self.student_loan_spin.setValue(int(s.get("loan_period_student", "15")))
        self.teacher_loan_spin.setValue(int(s.get("loan_period_teacher", "30")))
        self.fine_spin.setValue(float(s.get("fine_per_day", "2.0")))
        self.smtp_host_edit.setText(s.get("email_host", "smtp.gmail.com"))
        self.smtp_port_spin.setValue(int(s.get("email_port", "587")))
        self.email_user_edit.setText(s.get("email_user", ""))
        self.email_pass_edit.setText(s.get("email_password", ""))
        self.email_from_edit.setText(s.get("email_from", ""))

    def _save_library_settings(self):
        set_setting("library_name", self.lib_name_edit.text().strip())
        set_setting("loan_period_student", str(self.student_loan_spin.value()))
        set_setting("loan_period_teacher", str(self.teacher_loan_spin.value()))
        set_setting("fine_per_day", str(self.fine_spin.value()))
        QMessageBox.information(self, "Saved", "✅ Library settings saved successfully!")

    def _save_email_settings(self):
        set_setting("email_host", self.smtp_host_edit.text().strip())
        set_setting("email_port", str(self.smtp_port_spin.value()))
        set_setting("email_user", self.email_user_edit.text().strip())
        set_setting("email_password", self.email_pass_edit.text())
        set_setting("email_from", self.email_from_edit.text().strip())
        QMessageBox.information(self, "Saved", "✅ Email settings saved successfully!")

    def _send_test_email(self):
        to = self.email_user_edit.text().strip()
        if not to:
            QMessageBox.warning(self, "No Email", "Enter your email address first.")
            return

        success, err = send_email(
            to_addr=to,
            subject="[SRM Library] Test Email",
            body_html="<h2>✅ Email is working!</h2><p>Your SRM Library email configuration is correct.</p>",
            smtp_host=self.smtp_host_edit.text().strip(),
            smtp_port=self.smtp_port_spin.value(),
            smtp_user=self.email_user_edit.text().strip(),
            smtp_password=self.email_pass_edit.text(),
        )
        if success:
            QMessageBox.information(self, "Test Passed", f"✅ Test email sent to {to}!")
        else:
            QMessageBox.critical(self, "Test Failed", f"❌ Error: {err}")
