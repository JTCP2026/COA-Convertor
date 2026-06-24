"""
pdf_parser.py
Extracts text and tables from PDF files.
Strategy: PyMuPDF (fitz) for text → pdfplumber for tables → pytesseract OCR fallback.
"""
from __future__ import annotations
import io
import logging
import re
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class ParsedDocument:
    text: str = ""
    tables: list[list[list[str]]] = field(default_factory=list)
    source_type: str = "unknown"   # "pdf_text" | "pdf_ocr" | "docx"
    page_count: int = 0
    # Populated only when the page matches the borderless "industry standard"
    # COA layout (label/value grid + 4-col analysis table with no ruled
    # lines) — see _extract_structured_coa(). None when not detected.
    structured: dict | None = None


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

    # If pdfplumber's line-based table detection degenerated (everything
    # dumped into column 0 — typical of borderless industry-standard COA
    # layouts), fall back to a position-based structured extraction.
    if _tables_look_degenerate(doc_result.tables):
        try:
            doc_result.structured = _extract_structured_coa(path)
        except Exception as e:
            log.warning("structured COA extraction failed: %s", e)

    return doc_result


def _tables_look_degenerate(tables: list[list[list[str]]]) -> bool:
    """True if every multi-column table has all its content crammed into
    column 0 with the other columns empty/None — a sign the source PDF has
    no ruled lines and pdfplumber's lines-strategy failed to find columns."""
    if not tables:
        return True
    for table in tables:
        for row in table[1:]:
            non_empty = [c for c in row if c and str(c).strip()]
            if len(non_empty) > 1:
                return False
    return True


# ---------------------------------------------------------------------------
# Structured, position-based extraction for the borderless "industry
# standard" supplier COA layout: a 2-column-pair label/value grid (Product
# name / Botanical name / ... | Batch no. / Production date / ...) followed
# by a 4-column analysis table (Analysis item | Specification | Result |
# Analysis test method) with category banner rows and no ruled lines.
# ---------------------------------------------------------------------------

# Label-keyword matching is shared with field_mapper.py (used there for the
# ruled-line-table case) so both extraction paths recognize the same wording.
from .field_mapper import match_grid_label as _match_grid_label
from .field_mapper import match_header_col as _match_header_col

_DISCLAIMER_LEN_THRESHOLD = 40


def _line_words(words: list[tuple]) -> dict[tuple[int, int], list[tuple]]:
    from collections import defaultdict as _dd
    lines: dict[tuple[int, int], list[tuple]] = _dd(list)
    for w in words:
        lines[(w[5], w[6])].append(w)
    return lines


def _extract_structured_coa(path: str) -> dict | None:
    import fitz

    pdf = fitz.open(path)
    try:
        page = pdf[0]
        words = page.get_text("words")
        lines = _line_words(words)
        ordered_keys = sorted(lines.keys())

        line_texts: list[tuple[tuple[int, int], float, str]] = []
        for key in ordered_keys:
            ws = sorted(lines[key], key=lambda w: w[0])
            text = " ".join(w[4] for w in ws)
            line_texts.append((key, ws[0][0], text))

        # ── Locate the header grid (Product name / Batch no. / ...) ──────────
        header_fields: dict[str, str] = {}
        grid_start_idx = None
        for i, (_, x0, text) in enumerate(line_texts):
            if _match_grid_label(text):
                grid_start_idx = i
                break
        table_start_idx = None
        for i, (_, x0, text) in enumerate(line_texts):
            if _match_header_col(text) == 0:
                table_start_idx = i
                break

        if grid_start_idx is None or table_start_idx is None:
            return None  # doesn't match this layout

        left_label_x = line_texts[grid_start_idx][1]
        right_label_x = None
        for _, x0, text in line_texts[grid_start_idx:table_start_idx]:
            if _match_grid_label(text) and x0 > left_label_x + 50:
                right_label_x = x0
                break
        if right_label_x is None:
            return None
        threshold_x = (left_label_x + right_label_x) / 2

        left_seq, right_seq = [], []
        for _, x0, text in line_texts[grid_start_idx:table_start_idx]:
            (left_seq if x0 < threshold_x else right_seq).append(text)

        for seq in (left_seq, right_seq):
            for i in range(0, len(seq) - 1, 2):
                field_name = _match_grid_label(seq[i])
                if field_name:
                    header_fields[field_name] = seq[i + 1].strip()

        # ── Locate the 4-column analysis table ────────────────────────────────
        hdr_key, hdr_x0, hdr_text = line_texts[table_start_idx]
        # Re-derive per-cell x0 for the 4 header phrases — they may span
        # multiple fitz "lines" if the header wraps, so search forward a few
        # entries for whichever column-keyword set comes next.
        col_bounds = [hdr_x0]
        search_end = min(table_start_idx + 6, len(line_texts))
        j = table_start_idx + 1
        next_col = 1
        while j < search_end and next_col < 4:
            _, x0, text = line_texts[j]
            if _match_header_col(text) == next_col:
                col_bounds.append(x0)
                next_col += 1
            j += 1
        if len(col_bounds) != 4:
            return None

        def _col_of(x0: float) -> int:
            col = 0
            for b in col_bounds[1:]:
                if x0 >= b - 2:
                    col += 1
            return min(col, 3)

        test_results: list[dict] = []
        current_row: dict[int, str] = {}
        last_col = -1

        def _flush_row():
            nonlocal current_row
            if current_row:
                test_results.append(dict(current_row))
            current_row = {}

        for _, x0, text in line_texts[j:]:
            col = _col_of(x0)
            if col <= last_col:
                _flush_row()
            current_row[col] = text.strip()
            last_col = col

            # Stop at disclaimer / legal boilerplate: a long single-column line
            if len(current_row) == 1 and col == 0 and len(text.strip()) > _DISCLAIMER_LEN_THRESHOLD:
                current_row = {}
                break
        else:
            _flush_row()

        # Convert raw column rows into TestResult-shaped dicts, tracking bands
        parsed_rows = []
        current_band = ""
        for row in test_results:
            if set(row.keys()) == {0}:
                # category banner (only column 0 filled)
                current_band = re.sub(r"(?<=[A-Za-z])\d+$", "", row[0]).strip()
                continue
            parsed_rows.append({
                "test_name": re.sub(r"(?<=[A-Za-z])\d+$", "", row.get(0, "")).strip(),
                "category_label": current_band,
                "specification": row.get(1, ""),
                "result": row.get(2, ""),
                "method": row.get(3, ""),
            })

        return {"header_fields": header_fields, "test_results": parsed_rows}
    finally:
        pdf.close()


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
