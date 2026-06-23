"""
export_screen.py — Screen 4: Export COA as PDF or Word
"""
from __future__ import annotations
import os
import subprocess
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QMessageBox, QGroupBox,
    QFormLayout, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from core.coa_model import COADocument, FIELD_LABELS
from core.config_manager import load_config, next_cert_number
from datetime import date


class ExportScreen(QWidget):
    start_new = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._doc: COADocument | None = None
        self._last_output_dir = os.path.expanduser("~")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(14)

        title = QLabel("Export Certificate of Analysis")
        title.setObjectName("ScreenTitle")
        layout.addWidget(title)

        # Summary card
        summary_group = QGroupBox("COA Summary")
        self._summary_layout = QFormLayout(summary_group)
        self._summary_layout.setSpacing(7)
        self._summary_labels: dict[str, QLabel] = {}
        for key in ["product_name", "lot_number", "manufacturer_name",
                    "date_of_analysis", "expiry_date", "overall_disposition",
                    "certificate_number"]:
            lbl = QLabel("—")
            lbl.setWordWrap(True)
            self._summary_labels[key] = lbl
            self._summary_layout.addRow(
                QLabel(f"<b>{FIELD_LABELS.get(key, key)}:</b>"), lbl
            )
        layout.addWidget(summary_group)

        # Disposition highlight
        self._disp_banner = QLabel("")
        self._disp_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._disp_banner.setFixedHeight(40)
        self._disp_banner.setStyleSheet("font-size:15px; font-weight:bold; border-radius:6px;")
        layout.addWidget(self._disp_banner)

        # Export buttons
        export_group = QGroupBox("Export Options")
        export_layout = QHBoxLayout(export_group)
        export_layout.setSpacing(16)

        self._pdf_btn = QPushButton("Export as PDF")
        self._pdf_btn.setFixedHeight(44)
        self._pdf_btn.clicked.connect(self._export_pdf)

        self._docx_btn = QPushButton("Export as Word (.docx)")
        self._docx_btn.setObjectName("SecondaryBtn")
        self._docx_btn.setFixedHeight(44)
        self._docx_btn.clicked.connect(self._export_docx)

        self._open_folder_btn = QPushButton("Open Output Folder")
        self._open_folder_btn.setObjectName("SecondaryBtn")
        self._open_folder_btn.setEnabled(False)
        self._open_folder_btn.clicked.connect(self._open_folder)

        export_layout.addWidget(self._pdf_btn)
        export_layout.addWidget(self._docx_btn)
        export_layout.addWidget(self._open_folder_btn)
        layout.addWidget(export_group)

        # Export status
        self._export_status = QLabel("")
        self._export_status.setStyleSheet("font-size:12px; color:#1A7A4A;")
        layout.addWidget(self._export_status)

        layout.addStretch()

        # Start new button
        bottom_row = QHBoxLayout()
        new_btn = QPushButton("← Start New Conversion")
        new_btn.setObjectName("SecondaryBtn")
        new_btn.clicked.connect(self.start_new.emit)
        bottom_row.addWidget(new_btn)
        bottom_row.addStretch()
        layout.addLayout(bottom_row)

    def load(self, doc: COADocument):
        cfg = load_config()

        # Auto-assign cert number if missing
        if not doc.certificate_number:
            doc.certificate_number = next_cert_number(cfg)
        if not doc.date_of_analysis:
            doc.date_of_analysis = date.today().strftime("%Y-%m-%d")

        # Fill from company config
        doc.receiving_company_name = cfg.company_name
        doc.receiving_company_address = cfg.address
        doc.receiving_company_logo_path = cfg.logo_path
        doc.receiving_company_header_path = cfg.header_path
        if not doc.qc_release_statement:
            doc.qc_release_statement = cfg.qc_release_statement
        if not doc.authorised_signatory_name:
            doc.authorised_signatory_name = cfg.signatory_name
        if not doc.authorised_signatory_title:
            doc.authorised_signatory_title = cfg.signatory_title

        self._doc = doc

        # Update summary
        for key, lbl in self._summary_labels.items():
            lbl.setText(getattr(doc, key, "") or "—")

        # Disposition banner
        disp = doc.overall_disposition
        if "PASS" in disp:
            self._disp_banner.setText(f"✓  {disp}")
            self._disp_banner.setStyleSheet(
                "font-size:15px; font-weight:bold; border-radius:6px; "
                "background:#E8F5E9; color:#1A7A4A;"
            )
        elif "FAIL" in disp:
            self._disp_banner.setText(f"✗  {disp}")
            self._disp_banner.setStyleSheet(
                "font-size:15px; font-weight:bold; border-radius:6px; "
                "background:#FFEBEE; color:#C0392B;"
            )
        else:
            self._disp_banner.setText(f"⚠  {disp}")
            self._disp_banner.setStyleSheet(
                "font-size:15px; font-weight:bold; border-radius:6px; "
                "background:#FFF8E1; color:#F57F17;"
            )

        self._export_status.setText("")
        self._open_folder_btn.setEnabled(False)

    def _export_pdf(self):
        if not self._doc:
            return
        default_name = f"COA_{self._doc.product_name or 'output'}_{self._doc.lot_number or ''}.pdf"
        default_name = default_name.replace(" ", "_")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF", os.path.join(self._last_output_dir, default_name),
            "PDF Files (*.pdf)"
        )
        if not path:
            return
        try:
            from generators.pdf_generator import generate_pdf
            generate_pdf(self._doc, path)
            self._last_output_dir = os.path.dirname(path)
            self._open_folder_btn.setEnabled(True)
            self._export_status.setText(f"✓ PDF saved: {os.path.basename(path)}")
            QMessageBox.information(self, "Export Complete",
                                    f"PDF saved successfully:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not generate PDF:\n{e}")

    def _export_docx(self):
        if not self._doc:
            return
        default_name = f"COA_{self._doc.product_name or 'output'}_{self._doc.lot_number or ''}.docx"
        default_name = default_name.replace(" ", "_")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Word Document", os.path.join(self._last_output_dir, default_name),
            "Word Documents (*.docx)"
        )
        if not path:
            return
        try:
            from generators.docx_generator import generate_docx
            generate_docx(self._doc, path)
            self._last_output_dir = os.path.dirname(path)
            self._open_folder_btn.setEnabled(True)
            self._export_status.setText(f"✓ Word document saved: {os.path.basename(path)}")
            QMessageBox.information(self, "Export Complete",
                                    f"Word document saved successfully:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not generate Word document:\n{e}")

    def _open_folder(self):
        if sys.platform == "win32":
            os.startfile(self._last_output_dir)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", self._last_output_dir])
        else:
            subprocess.Popen(["xdg-open", self._last_output_dir])
