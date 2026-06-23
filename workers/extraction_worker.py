"""
extraction_worker.py
QThread worker that parses a supplier document and maps fields to COADocument.
Runs in background to keep the UI responsive.
"""
from __future__ import annotations
import os
from PyQt6.QtCore import QThread, pyqtSignal
from core.coa_model import COADocument
from core.field_mapper import FieldConfidence, map_from_text, map_from_tables, merge_documents


class ExtractionWorker(QThread):
    progress = pyqtSignal(int)          # 0–100
    raw_text_ready = pyqtSignal(str)    # emit raw text for preview
    finished = pyqtSignal(object, object)  # (COADocument, FieldConfidence)
    error = pyqtSignal(str)

    def __init__(self, file_path: str, extra_aliases: dict | None = None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.extra_aliases = extra_aliases or {}

    def run(self):
        try:
            ext = os.path.splitext(self.file_path)[1].lower()
            if ext == ".pdf":
                from core.pdf_parser import parse_pdf
                parsed = parse_pdf(self.file_path, progress_callback=self.progress.emit)
            elif ext in (".docx", ".doc"):
                from core.docx_parser import parse_docx
                parsed = parse_docx(self.file_path, progress_callback=self.progress.emit)
            else:
                self.error.emit(f"Unsupported file type: {ext}")
                return

            self.raw_text_ready.emit(parsed.text[:5000])
            self.progress.emit(96)

            # Map fields from free text
            text_doc, text_conf = map_from_text(parsed.text, self.extra_aliases)
            self.progress.emit(98)

            # Map test results from tables (higher confidence)
            table_results, table_conf = map_from_tables(parsed.tables)

            # Merge
            final_doc, final_conf = merge_documents(text_doc, text_conf, table_results, table_conf)
            self.progress.emit(100)
            self.finished.emit(final_doc, final_conf)

        except Exception as e:
            self.error.emit(str(e))
