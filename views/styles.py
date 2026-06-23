"""Shared Qt Style Sheet for the COA Converter application."""

QSS = """
/* ── Global ─────────────────────────────────────────────── */
QMainWindow, QDialog {
    background-color: #F0F2F5;
}
QWidget {
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    color: #222222;
}

/* ── Sidebar ─────────────────────────────────────────────── */
#Sidebar {
    background-color: #0D2B55;
    min-width: 190px;
    max-width: 190px;
}
#SidebarTitle {
    color: #C9A84C;
    font-size: 15px;
    font-weight: bold;
    padding: 18px 16px 6px 16px;
}
#SidebarSubtitle {
    color: #8BAFD4;
    font-size: 10px;
    padding: 0px 16px 18px 16px;
}
QPushButton#NavBtn {
    background-color: transparent;
    color: #B8D0E8;
    border: none;
    text-align: left;
    padding: 12px 16px;
    font-size: 13px;
    border-radius: 0px;
}
QPushButton#NavBtn:hover {
    background-color: #163B70;
    color: #FFFFFF;
}
QPushButton#NavBtn[active="true"] {
    background-color: #1E4D8C;
    color: #FFFFFF;
    border-left: 3px solid #C9A84C;
    padding-left: 13px;
}

/* ── Content area ────────────────────────────────────────── */
#ContentArea {
    background-color: #FFFFFF;
    border-radius: 8px;
    margin: 10px;
}

/* ── Section headers inside screens ─────────────────────── */
QLabel#ScreenTitle {
    font-size: 20px;
    font-weight: bold;
    color: #0D2B55;
    padding-bottom: 4px;
}
QLabel#SectionLabel {
    font-size: 11px;
    font-weight: bold;
    color: #FFFFFF;
    background-color: #0D2B55;
    padding: 6px 10px;
    border-radius: 3px;
}

/* ── Form fields ─────────────────────────────────────────── */
QLineEdit, QTextEdit, QComboBox, QDateEdit {
    background-color: #FFFFFF;
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 12px;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border: 1.5px solid #0D2B55;
}
QLineEdit[confidence="low"] {
    background-color: #FFF8E1;
    border: 1px solid #F9A825;
}
QLineEdit[confidence="very_low"] {
    background-color: #FFF3E0;
    border: 1px solid #E65100;
}
QLineEdit[readonly="true"] {
    background-color: #F5F5F5;
    color: #555555;
}

/* ── Buttons ─────────────────────────────────────────────── */
QPushButton {
    background-color: #0D2B55;
    color: #FFFFFF;
    border: none;
    border-radius: 5px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #1E4D8C;
}
QPushButton:pressed {
    background-color: #0A1E3D;
}
QPushButton:disabled {
    background-color: #AAAAAA;
    color: #FFFFFF;
}
QPushButton#SecondaryBtn {
    background-color: #FFFFFF;
    color: #0D2B55;
    border: 1.5px solid #0D2B55;
}
QPushButton#SecondaryBtn:hover {
    background-color: #EBF0F8;
}
QPushButton#GoldBtn {
    background-color: #C9A84C;
    color: #FFFFFF;
}
QPushButton#GoldBtn:hover {
    background-color: #B8962A;
}
QPushButton#DangerBtn {
    background-color: #C0392B;
    color: #FFFFFF;
}
QPushButton#DangerBtn:hover {
    background-color: #A93226;
}

/* ── Drop zone ───────────────────────────────────────────── */
#DropZone {
    border: 2px dashed #0D2B55;
    border-radius: 10px;
    background-color: #F0F4FA;
    color: #0D2B55;
    font-size: 14px;
    padding: 30px;
}
#DropZone[drag="true"] {
    border: 2px dashed #C9A84C;
    background-color: #FFFBF0;
}

/* ── Table widget ────────────────────────────────────────── */
QTableWidget {
    border: 1px solid #CCCCCC;
    gridline-color: #E0E0E0;
    background-color: #FFFFFF;
    alternate-background-color: #F5F7FA;
    selection-background-color: #D0DEEF;
}
QTableWidget::item {
    padding: 4px 6px;
}
QHeaderView::section {
    background-color: #0D2B55;
    color: #FFFFFF;
    font-weight: bold;
    padding: 6px 8px;
    border: none;
    font-size: 11px;
}

/* ── Progress bar ────────────────────────────────────────── */
QProgressBar {
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    text-align: center;
    height: 18px;
}
QProgressBar::chunk {
    background-color: #0D2B55;
    border-radius: 3px;
}

/* ── Group box ───────────────────────────────────────────── */
QGroupBox {
    border: 1px solid #CCCCCC;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: bold;
    color: #0D2B55;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}

/* ── Scroll area ─────────────────────────────────────────── */
QScrollArea {
    border: none;
    background-color: transparent;
}
"""
