"""
upload_screen.py — Screen 2: File Upload & Extraction
"""
from __future__ import annotations
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QProgressBar, QFileDialog, QMessageBox, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from core.coa_model import COADocument
from core.field_mapper import FieldConfidence
from workers.extraction_worker import ExtractionWorker


class DropZone(QLabel):
    file_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("⬇  Drag & drop supplier document here\n\nSupported: PDF, DOCX")
        self.setFixedHeight(160)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            urls = e.mimeData().urls()
            if any(u.toLocalFile().lower().endswith((".pdf", ".docx", ".doc")) for u in urls):
                e.acceptProposedAction()
                self.setProperty("drag", "true")
                self.style().unpolish(self)
                self.style().polish(self)

    def dragLeaveEvent(self, e):
        self.setProperty("drag", "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, e: QDropEvent):
        self.setProperty("drag", "false")
        self.style().unpolish(self)
        self.style().polish(self)
        for url in e.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith((".pdf", ".docx", ".doc")):
                self.file_dropped.emit(path)
                break


class UploadScreen(QWidget):
    extraction_done = pyqtSignal(object, object)  # (COADocument, FieldConfidence)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_path = ""
        self._worker: ExtractionWorker | None = None
        self._extra_aliases: dict = {}
        self._init_ui()

    def set_aliases(self, aliases: dict):
        self._extra_aliases = aliases

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(14)

        title = QLabel("Upload Supplier Document")
        title.setObjectName("ScreenTitle")
        layout.addWidget(title)

        subtitle = QLabel("Upload a supplier Certificate of Analysis (PDF or Word). "
                          "Fields will be extracted automatically.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#555; font-size:12px;")
        layout.addWidget(subtitle)

        # Drop zone
        self._drop_zone = DropZone()
        self._drop_zone.file_dropped.connect(self._on_file_selected)
        layout.addWidget(self._drop_zone)

        # Browse button row
        browse_row = QHBoxLayout()
        self._browse_btn = QPushButton("Browse File…")
        self._browse_btn.setObjectName("SecondaryBtn")
        self._browse_btn.setFixedWidth(160)
        self._browse_btn.clicked.connect(self._browse)
        self._file_label = QLabel("No file selected")
        self._file_label.setStyleSheet("color:#666; font-size:12px;")
        browse_row.addWidget(self._browse_btn)
        browse_row.addWidget(self._file_label)
        browse_row.addStretch()
        layout.addLayout(browse_row)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setValue(0)
        layout.addWidget(self._progress)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("font-size:11px; color:#555;")
        layout.addWidget(self._status_label)

        # Raw text preview
        preview_label = QLabel("Extracted Text Preview")
        preview_label.setObjectName("SectionLabel")
        layout.addWidget(preview_label)

        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setPlaceholderText("Raw text from the supplier document will appear here after extraction…")
        self._preview.setFixedHeight(180)
        layout.addWidget(self._preview)

        # Extract button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._extract_btn = QPushButton("Extract & Continue →")
        self._extract_btn.setEnabled(False)
        self._extract_btn.clicked.connect(self._start_extraction)
        btn_row.addWidget(self._extract_btn)
        layout.addLayout(btn_row)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Supplier Document", "",
            "Documents (*.pdf *.docx *.doc)"
        )
        if path:
            self._on_file_selected(path)

    def _on_file_selected(self, path: str):
        self._file_path = path
        self._file_label.setText(os.path.basename(path))
        self._file_label.setStyleSheet("color:#0D2B55; font-weight:bold; font-size:12px;")
        self._extract_btn.setEnabled(True)
        self._preview.clear()
        self._status_label.setText("")
        self._progress.setVisible(False)
        self._drop_zone.setText(
            f"✓  File loaded: {os.path.basename(path)}\n\nClick 'Extract & Continue' to process."
        )

    def _start_extraction(self):
        if not self._file_path:
            return
        self._extract_btn.setEnabled(False)
        self._browse_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._status_label.setText("Parsing document…")

        self._worker = ExtractionWorker(self._file_path, self._extra_aliases)
        self._worker.progress.connect(self._progress.setValue)
        self._worker.raw_text_ready.connect(self._preview.setPlainText)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, doc: COADocument, conf: FieldConfidence):
        self._progress.setValue(100)
        self._status_label.setText("✓ Extraction complete — review fields on the next screen.")
        self._status_label.setStyleSheet("font-size:11px; color:#1A7A4A; font-weight:bold;")
        self._extract_btn.setEnabled(True)
        self._browse_btn.setEnabled(True)
        self.extraction_done.emit(doc, conf)

    def _on_error(self, msg: str):
        self._progress.setVisible(False)
        self._extract_btn.setEnabled(True)
        self._browse_btn.setEnabled(True)
        self._status_label.setText("")
        QMessageBox.critical(self, "Extraction Error",
                             f"Could not process the file:\n\n{msg}\n\n"
                             "Please check the file is not password-protected or corrupted.")

    def reset(self):
        self._file_path = ""
        self._file_label.setText("No file selected")
        self._file_label.setStyleSheet("color:#666; font-size:12px;")
        self._extract_btn.setEnabled(False)
        self._preview.clear()
        self._progress.setVisible(False)
        self._status_label.setText("")
        self._drop_zone.setText("⬇  Drag & drop supplier document here\n\nSupported: PDF, DOCX")
