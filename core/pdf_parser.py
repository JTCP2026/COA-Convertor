"""
pdf_parser.py
Extracts text and tables from PDF files.
Strategy: PyMuPDF (fitz) for text → pdfplumber for tables → pytesseract OCR fallback.
"""
from __future__ import annotations
import io
import logging
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class ParsedDocument:
    text: str = ""
    tables: list[list[list[str]]] = field(default_factory=list)
    source_type: str = "unknown"   # "pdf_text" | "pdf_ocr" | "docx"
    page_count: int = 0


def parse_pdf(path: str, progress_callback=None) -> ParsedDocument:
    """Parse a PDF file. Returns ParsedDocument."""
    import fitz  # PyMuPDF

    doc_result = ParsedDocument(source_type="pdf_text")

    try:
        pdf = fitz.open(path)
        doc_result.page_count = len(pdf)
        all_text_parts: list[str] = []
        low_text_pages: list[int] = []

        for page_num, page in enumerate(pdf):
            if progress_callback:
                progress_callback(int((page_num / len(pdf)) * 50))

            text = page.get_text("text")
            if len(text.strip()) < 30:
                low_text_pages.append(page_num)
            else:
                all_text_parts.append(text)

        # OCR for image-only pages
        if low_text_pages:
            doc_result.source_type = "pdf_ocr"
            ocr_text = _ocr_pages(pdf, low_text_pages, progress_callback)
            all_text_parts.extend(ocr_text)

        doc_result.text = "\n".join(all_text_parts)
        pdf.close()
    except Exception as e:
        log.error("PyMuPDF error: %s", e)

    # Extract tables with pdfplumber
    try:
        doc_result.tables = _extract_tables_pdfplumber(path, progress_callback)
    except Exception as e:
        log.warning("pdfplumber table extraction failed: %s", e)

    return doc_result


def _ocr_pages(pdf, page_indices: list[int], progress_callback=None) -> list[str]:
    """Run pytesseract OCR on specified page indices."""
    texts: list[str] = []
    try:
        import pytesseract
        from PIL import Image

        for i, page_num in enumerate(page_indices):
            if progress_callback:
                progress_callback(50 + int((i / len(page_indices)) * 40))
            page = pdf[page_num]
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = pytesseract.image_to_string(img, lang="eng+chi_sim")
            texts.append(text)
    except ImportError:
        log.warning("pytesseract not available — skipping OCR for image pages")
    except Exception as e:
        log.error("OCR error: %s", e)
    return texts


def _extract_tables_pdfplumber(path: str, progress_callback=None) -> list[list[list[str]]]:
    """Extract tables from PDF using pdfplumber."""
    import pdfplumber

    all_tables: list[list[list[str]]] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            try:
                tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)
            except Exception:
                pass
    if progress_callback:
        progress_callback(95)
    return all_tables
