"""
setup_screen.py — Screen 1: Company Setup & Configuration
First-run: full editable form.
After saved: read-only view with "Edit Company Information" button.
"""
from __future__ import annotations
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QFileDialog,
    QScrollArea, QMessageBox, QFrame, QGroupBox,
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, pyqtSignal
from core.config_manager import CompanyConfig, load_config, save_config, save_logo, save_header


class SetupScreen(QWidget):
    config_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._edit_mode = False
        self._cfg = load_config()
        self._init_ui()
        self._load_values()
        self._set_mode(not self._cfg.is_configured())  # edit if first run

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 20, 30, 20)
        root.setSpacing(12)

        # Title
        title = QLabel("Company Setup")
        title.setObjectName("ScreenTitle")
        root.addWidget(title)

        # Status bar (shown when already configured)
        self._status_bar = QLabel("✓  Company profile configured")
        self._status_bar.setStyleSheet(
            "background:#E8F5E9; color:#1A7A4A; padding:8px 12px; border-radius:4px; font-weight:bold;"
        )
        root.addWidget(self._status_bar)

        # Scrollable form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        form_widget = QWidget()
        self._form_layout = QFormLayout(form_widget)
        self._form_layout.setSpacing(10)
        self._form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        scroll.setWidget(form_widget)
        root.addWidget(scroll)

        def field(label, attr, multi=False, placeholder=""):
            if multi:
                w = QTextEdit()
                w.setFixedHeight(65)
                w.setPlaceholderText(placeholder)
            else:
                w = QLineEdit()
                w.setPlaceholderText(placeholder)
            setattr(self, f"_f_{attr}", w)
            self._form_layout.addRow(label, w)
            return w

        field("Company Name *", "company_name", placeholder="e.g. Acme Pharma Pty Ltd")
        field("Address", "address", multi=True, placeholder="Street, City, State, Postcode, Country")
        field("Phone", "phone", placeholder="+61 2 1234 5678")
        field("Email", "email", placeholder="qc@yourcompany.com")
        field("Website", "website", placeholder="www.yourcompany.com")

        # Logo upload row
        logo_row = QHBoxLayout()
        self._logo_preview = QLabel()
        self._logo_preview.setFixedSize(80, 40)
        self._logo_preview.setStyleSheet("border:1px solid #CCC; background:#FFF;")
        self._logo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._logo_path_label = QLabel("No logo uploaded")
        self._logo_path_label.setStyleSheet("color:#888; font-size:11px;")
        self._logo_btn = QPushButton("Browse Logo…")
        self._logo_btn.setObjectName("SecondaryBtn")
        self._logo_btn.setFixedWidth(130)
        self._logo_btn.clicked.connect(self._browse_logo)
        logo_row.addWidget(self._logo_preview)
        logo_row.addWidget(self._logo_path_label)
        logo_row.addStretch()
        logo_row.addWidget(self._logo_btn)
        self._form_layout.addRow("Company Logo", logo_row)

        # Header image upload row
        header_row = QHBoxLayout()
        self._header_preview = QLabel()
        self._header_preview.setFixedSize(420, 60)
        self._header_preview.setStyleSheet("border:1px solid #CCC; background:#FFF;")
        self._header_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._header_path_label = QLabel("No header uploaded")
        self._header_path_label.setStyleSheet("color:#888; font-size:11px;")
        self._header_btn = QPushButton("Browse Header…")
        self._header_btn.setObjectName("SecondaryBtn")
        self._header_btn.setFixedWidth(140)
        self._header_btn.clicked.connect(self._browse_header)
        self._header_remove_btn = QPushButton("Remove")
        self._header_remove_btn.setObjectName("DangerBtn")
        self._header_remove_btn.setFixedWidth(80)
        self._header_remove_btn.clicked.connect(self._remove_header)
        self._header_remove_btn.setVisible(False)
        header_row.addWidget(self._header_preview)
        header_row.addSpacing(8)
        header_row.addWidget(self._header_path_label)
        header_row.addStretch()
        header_row.addWidget(self._header_remove_btn)
        header_row.addWidget(self._header_btn)
        self._form_layout.addRow("Company Header\n(full-width banner)", header_row)

        field("QC Release Statement", "qc_release_statement", multi=True,
              placeholder="This material has been tested and meets all specified requirements…")
        field("Authorised Signatory", "signatory_name", placeholder="Full name")
        field("Signatory Title", "signatory_title", placeholder="e.g. Quality Control Manager")
        field("Certificate Prefix", "cert_prefix", placeholder="e.g. COA")

        # Alias section
        alias_group = QGroupBox("Custom Field Aliases  (one per line: alias → field)")
        alias_layout = QVBoxLayout(alias_group)
        self._alias_edit = QTextEdit()
        self._alias_edit.setFixedHeight(80)
        self._alias_edit.setPlaceholderText(
            "e.g.\n内部批号 → lot_number\nBBD → expiry_date"
        )
        alias_layout.addWidget(self._alias_edit)
        self._form_layout.addRow("", alias_group)

        # Buttons
        btn_row = QHBoxLayout()
        self._edit_btn = QPushButton("Edit Company Information")
        self._edit_btn.setObjectName("SecondaryBtn")
        self._edit_btn.clicked.connect(self._enter_edit)

        self._save_btn = QPushButton("Save Settings")
        self._save_btn.setObjectName("GoldBtn")
        self._save_btn.clicked.connect(self._save)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("SecondaryBtn")
        self._cancel_btn.clicked.connect(self._cancel_edit)

        btn_row.addWidget(self._edit_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._cancel_btn)
        btn_row.addWidget(self._save_btn)
        root.addLayout(btn_row)

    def _load_values(self):
        cfg = self._cfg
        self._f_company_name.setText(cfg.company_name)
        if hasattr(self._f_address, "setPlainText"):
            self._f_address.setPlainText(cfg.address)
        else:
            self._f_address.setText(cfg.address)
        self._f_phone.setText(cfg.phone)
        self._f_email.setText(cfg.email)
        self._f_website.setText(cfg.website)
        if hasattr(self._f_qc_release_statement, "setPlainText"):
            self._f_qc_release_statement.setPlainText(cfg.qc_release_statement)
        else:
            self._f_qc_release_statement.setText(cfg.qc_release_statement)
        self._f_signatory_name.setText(cfg.signatory_name)
        self._f_signatory_title.setText(cfg.signatory_title)
        self._f_cert_prefix.setText(cfg.cert_prefix)

        if cfg.logo_path and os.path.exists(cfg.logo_path):
            self._set_logo_preview(cfg.logo_path)
            self._logo_path_label.setText(os.path.basename(cfg.logo_path))

        if cfg.header_path and os.path.exists(cfg.header_path):
            self._set_header_preview(cfg.header_path)
            self._header_path_label.setText(os.path.basename(cfg.header_path))
            self._header_remove_btn.setVisible(True)
        else:
            self._header_preview.clear()
            self._header_path_label.setText("No header uploaded")
            self._header_remove_btn.setVisible(False)

        # Load aliases
        alias_lines = []
        for field_key, aliases in cfg.custom_aliases.items():
            for a in aliases:
                alias_lines.append(f"{a} → {field_key}")
        self._alias_edit.setPlainText("\n".join(alias_lines))

    def _set_logo_preview(self, path: str):
        pix = QPixmap(path)
        if not pix.isNull():
            self._logo_preview.setPixmap(
                pix.scaled(78, 38, Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
            )

    def _set_header_preview(self, path: str):
        pix = QPixmap(path)
        if not pix.isNull():
            self._header_preview.setPixmap(
                pix.scaled(418, 58, Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
            )

    def _browse_header(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Company Header Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self._cfg.header_path = path
            self._set_header_preview(path)
            self._header_path_label.setText(os.path.basename(path))
            self._header_remove_btn.setVisible(True)

    def _remove_header(self):
        self._cfg.header_path = ""
        self._header_preview.clear()
        self._header_path_label.setText("No header uploaded")
        self._header_remove_btn.setVisible(False)

    def _browse_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Company Logo", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.ico)"
        )
        if path:
            self._cfg.logo_path = path
            self._set_logo_preview(path)
            self._logo_path_label.setText(os.path.basename(path))

    def _set_mode(self, edit: bool):
        self._edit_mode = edit
        all_widgets = [
            self._f_company_name, self._f_address, self._f_phone,
            self._f_email, self._f_website, self._f_qc_release_statement,
            self._f_signatory_name, self._f_signatory_title,
            self._f_cert_prefix, self._alias_edit,
        ]
        for w in all_widgets:
            w.setReadOnly(not edit)
            w.setStyleSheet("background:#F5F5F5;" if not edit else "")
        self._logo_btn.setEnabled(edit)
        self._header_btn.setEnabled(edit)
        self._header_remove_btn.setEnabled(edit)
        self._status_bar.setVisible(not edit and self._cfg.is_configured())
        self._edit_btn.setVisible(not edit and self._cfg.is_configured())
        self._save_btn.setVisible(edit)
        self._cancel_btn.setVisible(edit and self._cfg.is_configured())

    def _enter_edit(self):
        self._set_mode(True)

    def _cancel_edit(self):
        self._load_values()
        self._set_mode(False)

    def _save(self):
        name = self._f_company_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Required Field", "Company Name is required.")
            return

        cfg = self._cfg
        cfg.company_name = name
        cfg.address = (self._f_address.toPlainText() if hasattr(self._f_address, "toPlainText")
                       else self._f_address.text())
        cfg.phone = self._f_phone.text().strip()
        cfg.email = self._f_email.text().strip()
        cfg.website = self._f_website.text().strip()
        cfg.qc_release_statement = (
            self._f_qc_release_statement.toPlainText()
            if hasattr(self._f_qc_release_statement, "toPlainText")
            else self._f_qc_release_statement.text()
        )
        cfg.signatory_name = self._f_signatory_name.text().strip()
        cfg.signatory_title = self._f_signatory_title.text().strip()
        cfg.cert_prefix = self._f_cert_prefix.text().strip() or "COA"

        if cfg.logo_path and os.path.exists(cfg.logo_path):
            try:
                cfg.logo_path = save_logo(cfg.logo_path)
            except Exception:
                pass

        if cfg.header_path and os.path.exists(cfg.header_path):
            try:
                cfg.header_path = save_header(cfg.header_path)
            except Exception:
                pass

        # Parse custom aliases
        aliases: dict[str, list[str]] = {}
        for line in self._alias_edit.toPlainText().splitlines():
            if "→" in line:
                parts = line.split("→", 1)
                alias = parts[0].strip()
                field_key = parts[1].strip()
                aliases.setdefault(field_key, []).append(alias)
        cfg.custom_aliases = aliases

        save_config(cfg)
        self._set_mode(False)
        self.config_saved.emit()
        QMessageBox.information(self, "Saved", "Company settings saved successfully.")
