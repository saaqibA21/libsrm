"""Shared styles and theme for the SRM Library System."""

# ─── Color Palette ────────────────────────────────────────────────────────────
PRIMARY = "#1565C0"
PRIMARY_DARK = "#0D47A1"
PRIMARY_LIGHT = "#1976D2"
ACCENT = "#00ACC1"
SUCCESS = "#2E7D32"
WARNING = "#F57F17"
DANGER = "#C62828"
BG_DARK = "#1E1E2E"
BG_CARD = "#252535"
BG_INPUT = "#2A2A3E"
TEXT_PRIMARY = "#E8EAF6"
TEXT_SECONDARY = "#9FA8DA"
TEXT_MUTED = "#616161"
BORDER = "#3A3A5C"

MAIN_STYLE = f"""
QMainWindow, QDialog {{
    background-color: {BG_DARK};
    color: {TEXT_PRIMARY};
}}

QWidget {{
    background-color: {BG_DARK};
    color: {TEXT_PRIMARY};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}}

/* ─── Sidebar ─────────────────────────────────────────────────────────── */
QFrame#sidebar {{
    background-color: {BG_CARD};
    border-right: 2px solid {BORDER};
}}

/* ─── Cards ──────────────────────────────────────────────────────────── */
QFrame#card {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}

/* ─── Buttons ────────────────────────────────────────────────────────── */
QPushButton {{
    background-color: {PRIMARY};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {PRIMARY_LIGHT};
}}
QPushButton:pressed {{
    background-color: {PRIMARY_DARK};
}}
QPushButton:disabled {{
    background-color: #424242;
    color: #757575;
}}

QPushButton#btn_success {{
    background-color: {SUCCESS};
}}
QPushButton#btn_success:hover {{
    background-color: #388E3C;
}}

QPushButton#btn_danger {{
    background-color: {DANGER};
}}
QPushButton#btn_danger:hover {{
    background-color: #D32F2F;
}}

QPushButton#btn_warning {{
    background-color: {WARNING};
    color: #1A1A1A;
}}
QPushButton#btn_warning:hover {{
    background-color: #F9A825;
}}

QPushButton#btn_secondary {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
}}
QPushButton#btn_secondary:hover {{
    background-color: {BORDER};
}}

/* Sidebar nav buttons */
QPushButton#nav_btn {{
    background-color: transparent;
    color: {TEXT_SECONDARY};
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 500;
    text-align: left;
}}
QPushButton#nav_btn:hover {{
    background-color: rgba(21,101,192,0.3);
    color: white;
}}
QPushButton#nav_btn[active="true"] {{
    background-color: {PRIMARY};
    color: white;
    font-weight: 700;
}}

/* ─── Inputs ──────────────────────────────────────────────────────────── */
QLineEdit, QTextEdit, QComboBox, QSpinBox, QDateEdit {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 13px;
    selection-background-color: {PRIMARY};
}}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 2px solid {PRIMARY_LIGHT};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    selection-background-color: {PRIMARY};
}}

/* ─── Tables ──────────────────────────────────────────────────────────── */
QTableWidget {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
    gridline-color: {BORDER};
    border: 1px solid {BORDER};
    border-radius: 8px;
    alternate-background-color: {BG_INPUT};
}}
QTableWidget::item {{
    padding: 6px 8px;
}}
QTableWidget::item:selected {{
    background-color: {PRIMARY};
    color: white;
}}
QHeaderView::section {{
    background-color: {PRIMARY_DARK};
    color: white;
    padding: 8px;
    border: none;
    font-weight: 600;
    font-size: 12px;
}}

/* ─── Labels ──────────────────────────────────────────────────────────── */
QLabel#title_label {{
    font-size: 22px;
    font-weight: 700;
    color: {TEXT_PRIMARY};
}}
QLabel#subtitle_label {{
    font-size: 13px;
    color: {TEXT_SECONDARY};
}}
QLabel#stat_number {{
    font-size: 32px;
    font-weight: 800;
    color: {PRIMARY_LIGHT};
}}
QLabel#stat_label {{
    font-size: 11px;
    color: {TEXT_SECONDARY};
    text-transform: uppercase;
}}

/* ─── Tabs ────────────────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    background-color: {BG_CARD};
    border-radius: 8px;
}}
QTabBar::tab {{
    background-color: {BG_INPUT};
    color: {TEXT_SECONDARY};
    padding: 8px 20px;
    border-radius: 6px 6px 0 0;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background-color: {PRIMARY};
    color: white;
    font-weight: 600;
}}

/* ─── ScrollBars ──────────────────────────────────────────────────────── */
QScrollBar:vertical {{
    width: 8px;
    background: {BG_DARK};
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    height: 8px;
    background: {BG_DARK};
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER};
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* ─── GroupBox ────────────────────────────────────────────────────────── */
QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 10px;
    font-weight: 600;
    color: {TEXT_SECONDARY};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    top: -8px;
    background-color: {BG_DARK};
    padding: 0 6px;
}}

/* ─── Splitter ───────────────────────────────────────────────────────── */
QSplitter::handle {{
    background: {BORDER};
}}

/* ─── Message Box ─────────────────────────────────────────────────────── */
QMessageBox {{
    background-color: {BG_CARD};
}}
QMessageBox QPushButton {{
    min-width: 80px;
}}

/* ─── Progress Bar ────────────────────────────────────────────────────── */
QProgressBar {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    height: 10px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {PRIMARY};
    border-radius: 6px;
}}
"""
