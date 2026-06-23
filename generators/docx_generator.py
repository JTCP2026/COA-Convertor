"""
docx_generator.py
COA Word doc — mirrors the PDF layout:
  3-col header → supplier block → shipment info → COA title →
  open test-results table (4 cols, category bold rows) → QC statement → signature block
"""
from __future__ import annotations
import os
from collections import defaultdict
from datetime import date
from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from core.coa_model import COADocument, PassFail, TestCategory

BLACK = RGBColor(0x00, 0x00, 0x00)
DGRAY = RGBColor(0x55, 0x55, 0x55)
LGRAY = RGBColor(0xF0, 0xF0, 0xF0)
GREEN = RGBColor(0x1A, 0x7A, 0x4A)
RED   = RGBColor(0xC0, 0x39, 0x2B)
NAVY  = RGBColor(0x0D, 0x2B, 0x55)

_CATEGORY_ORDER = [
    TestCategory.PHYSICAL.value,
    TestCategory.CHEMICAL.value,
    TestCategory.MICROBIOLOGICAL.value,
    TestCategory.OTHER.value,
]
_CATEGORY_LABELS = {
    TestCategory.PHYSICAL.value:        "Physical Characteristics",
    TestCategory.CHEMICAL.value:        "Chemical Properties",
    TestCategory.MICROBIOLOGICAL.value: "Microbiological Data",
    TestCategory.OTHER.value:           "Other",
}


def _hex(rgb: RGBColor) -> str:
    return f"{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


def _set_cell_bg(cell, rgb: RGBColor):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), _hex(rgb))
    tcPr.append(shd)


def _cell_para(cell, text: str, bold=False, italic=False,
               color: RGBColor | None = None, font_size: float = 9,
               align=WD_ALIGN_PARAGRAPH.LEFT) -> None:
    cell.paragraphs[0].clear()
    para = cell.paragraphs[0]
    para.alignment = align
    if text:
        run = para.add_run(text)
        run.bold = bold
        run.italic = italic
        run.font.size = Pt(font_size)
        if color:
            run.font.color.rgb = color


def _add_bottom_border(cell, color_hex="000000", size=6):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    bot = OxmlElement("w:bottom")
    bot.set(qn("w:val"), "single")
    bot.set(qn("w:sz"), str(size))
    bot.set(qn("w:color"), color_hex)
    tcBorders.append(bot)
    tcPr.append(tcBorders)


def _add_para(doc: Document, text: str, bold=False, italic=False,
              font_size: float = 9, color: RGBColor | None = None,
              align=WD_ALIGN_PARAGRAPH.LEFT, space_after: float = 0) -> None:
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    if text:
        r = p.add_run(text)
        r.bold = bold
        r.italic = italic
        r.font.size = Pt(font_size)
        if color:
            r.font.color.rgb = color


def _add_hr(doc: Document):
    """Add a horizontal rule paragraph."""
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "888888")
    pBdr.append(bottom)
    pPr.append(pBdr)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)


def generate_docx(coa: COADocument, output_path: str) -> None:
    doc = Document()

    for section in doc.sections:
        section.top_margin    = Cm(1.8)
        section.bottom_margin = Cm(1.8)
        section.left_margin   = Cm(1.8)
        section.right_margin  = Cm(1.8)

    # ── 1. COMPANY HEADER ─────────────────────────────────────────────────────
    if coa.receiving_company_header_path and os.path.exists(coa.receiving_company_header_path):
        try:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(coa.receiving_company_header_path, width=Inches(6.3))
        except Exception:
            pass
    else:
        ht = doc.add_table(rows=1, cols=3)
        ht.style = "Table Grid"
        lc = ht.cell(0, 0)
        cc = ht.cell(0, 1)
        rc = ht.cell(0, 2)

        # Left: QC contact
        _cell_para(lc, coa.authorised_signatory_name or "", font_size=8, color=DGRAY)
        if coa.authorised_signatory_title:
            lc.add_paragraph(coa.authorised_signatory_title).runs[0].font.size = Pt(8)

        # Center: logo or company name
        if coa.receiving_company_logo_path and os.path.exists(coa.receiving_company_logo_path):
            try:
                p = cc.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.add_run().add_picture(coa.receiving_company_logo_path, width=Cm(4))
            except Exception:
                _cell_para(cc, coa.receiving_company_name or "", bold=True, font_size=12,
                           color=NAVY, align=WD_ALIGN_PARAGRAPH.CENTER)
        else:
            _cell_para(cc, coa.receiving_company_name or "", bold=True, font_size=12,
                       color=NAVY, align=WD_ALIGN_PARAGRAPH.CENTER)

        # Right: company address
        _cell_para(rc, coa.receiving_company_name or "", bold=True, font_size=8,
                   align=WD_ALIGN_PARAGRAPH.RIGHT)
        for part in (coa.receiving_company_address or "").split("\n"):
            if part.strip():
                p2 = rc.add_paragraph(part.strip())
                p2.runs[0].font.size = Pt(8)
                p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT

        for cell, w in zip([lc, cc, rc], [Cm(4.5), Cm(7.5), Cm(4.5)]):
            cell.width = w

    _add_hr(doc)

    # ── 2. SUPPLIER / SUBJECT COMPANY BLOCK ──────────────────────────────────
    supplier_name = coa.supplier_name or coa.manufacturer_name
    if supplier_name:
        _add_para(doc, supplier_name, bold=True, font_size=15,
                  align=WD_ALIGN_PARAGRAPH.CENTER)
    if coa.manufacturer_address:
        for line in coa.manufacturer_address.split("\n"):
            if line.strip():
                _add_para(doc, line.strip(), font_size=9, color=DGRAY,
                          align=WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_paragraph()

    # ── 3. SHIPMENT / PRODUCT INFO BLOCK ─────────────────────────────────────
    info_rows = [
        ("SUPPLIER NAME & LOCATION",
         f"{supplier_name or '—'}"
         + (f", {coa.manufacturer_address.replace(chr(10), ', ')}" if coa.manufacturer_address else "")),
        ("INGREDIENT NAME",      coa.product_name),
        ("INGREDIENT NUMBER",    coa.internal_item_code or coa.supplier_product_code),
        ("PURCHASE ORDER #",     coa.purchase_order_number),
        ("DATE OF ANALYSIS",     coa.date_of_analysis),
        ("DATE OF SHIPMENT",     coa.manufacturing_date or coa.date_received),
        ("EXPIRY / RETEST DATE", coa.expiry_date or coa.retest_date),
        ("CERTIFICATE NO.",      coa.certificate_number),
        ("LOT NUMBER",           coa.lot_number),
    ]
    info_rows = [(lbl, val) for lbl, val in info_rows if val and str(val).strip()]

    if info_rows:
        it = doc.add_table(rows=len(info_rows), cols=2)
        it.style = "Table Grid"
        for i, (lbl, val) in enumerate(info_rows):
            cells = it.row_cells(i)
            _cell_para(cells[0], f"{lbl}:", bold=True, font_size=9)
            _cell_para(cells[1], str(val), font_size=9)
            cells[0].width = Cm(5.5)
            cells[1].width = Cm(11.0)

    doc.add_paragraph()
    _add_hr(doc)

    # ── 4. COA TITLE ─────────────────────────────────────────────────────────
    _add_para(doc, "CERTIFICATE OF ANALYSIS", bold=True, font_size=14,
              align=WD_ALIGN_PARAGRAPH.CENTER)
    _add_para(doc, "Analytical Data for This Shipment", italic=True, font_size=9,
              color=DGRAY, align=WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_paragraph()

    # ── 5. TEST RESULTS TABLE ─────────────────────────────────────────────────
    if coa.test_results:
        grouped: dict[str, list] = defaultdict(list)
        for tr in coa.test_results:
            cat = tr.category if tr.category in _CATEGORY_LABELS else TestCategory.OTHER.value
            grouped[cat].append(tr)

        # Count rows: header + category headers + data rows
        n_cat  = sum(1 for c in _CATEGORY_ORDER if grouped.get(c))
        n_data = len(coa.test_results)
        total  = 1 + n_cat + n_data

        t = doc.add_table(rows=total, cols=4)
        t.style = "Table Grid"
        col_widths = [Cm(4.5), Cm(3.8), Cm(3.8), Cm(4.4)]
        hdrs = ["Attribute", "Method Reference", "Specification", "Test Results"]

        # Header row
        hdr_cells = t.row_cells(0)
        for j, (cell, h, w) in enumerate(zip(hdr_cells, hdrs, col_widths)):
            _cell_para(cell, h, bold=True, font_size=9)
            _add_bottom_border(cell, "000000", 12)
            cell.width = w

        row_idx = 1
        for cat in _CATEGORY_ORDER:
            if not grouped.get(cat):
                continue

            # Category row: merge all 4 cols
            cat_cells = t.row_cells(row_idx)
            cat_cells[0].merge(cat_cells[3])
            _set_cell_bg(cat_cells[0], LGRAY)
            _cell_para(cat_cells[0], _CATEGORY_LABELS[cat], bold=True, font_size=9)
            row_idx += 1

            for tr in grouped[cat]:
                cells = t.row_cells(row_idx)
                result_text = f"{tr.result} {tr.unit}".strip() if tr.unit else (tr.result or "")
                result_color = (
                    GREEN if tr.pass_fail == PassFail.PASS.value
                    else RED if tr.pass_fail == PassFail.FAIL.value
                    else None
                )
                _cell_para(cells[0], tr.test_name or "", font_size=8.5)
                _cell_para(cells[1], tr.method or "", font_size=8.5)
                _cell_para(cells[2], tr.specification or "", font_size=8.5)
                _cell_para(cells[3], result_text, font_size=8.5, color=result_color)
                for cell, w in zip(cells, col_widths):
                    cell.width = w
                row_idx += 1

    else:
        doc.add_paragraph("No test results recorded.")

    doc.add_paragraph()
    _add_hr(doc)

    # ── 6. QC RELEASE STATEMENT ───────────────────────────────────────────────
    qc_text = (
        coa.qc_release_statement or
        "This item is regularly tested and meets all requirements defined by the appropriate "
        "current ingredient specification. This item is manufactured, packaged, stored, and "
        "shipped in accordance with Good Manufacturing Practices and under modern sanitary conditions."
    )
    _add_para(doc, qc_text, italic=True, font_size=8.5, color=DGRAY,
              align=WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_paragraph()
    _add_hr(doc)

    # ── 7. SIGNATURE BLOCK ────────────────────────────────────────────────────
    sig_date = coa.signature_date or date.today().strftime("%B %d %Y")
    st = doc.add_table(rows=4, cols=3)
    st.style = "Table Grid"

    # Row 0: signature space | title | date
    _cell_para(st.cell(0, 0), "", font_size=14)   # blank space for wet signature
    _cell_para(st.cell(0, 1), coa.authorised_signatory_title or "Quality Control Manager", font_size=9)
    _cell_para(st.cell(0, 2), sig_date, font_size=9)

    # Row 1: labels
    _cell_para(st.cell(1, 0), "Name", font_size=8, color=DGRAY)
    _cell_para(st.cell(1, 1), "Title", font_size=8, color=DGRAY)
    _cell_para(st.cell(1, 2), "Date", font_size=8, color=DGRAY)

    # Row 2: printed name | phone | email
    _cell_para(st.cell(2, 0), coa.authorised_signatory_name or "", bold=True, font_size=9)
    _cell_para(st.cell(2, 1), "", font_size=9)
    _cell_para(st.cell(2, 2), "", font_size=9)

    # Row 3: labels
    _cell_para(st.cell(3, 0), "Printed Name", font_size=8, color=DGRAY)
    _cell_para(st.cell(3, 1), "Phone Number", font_size=8, color=DGRAY)
    _cell_para(st.cell(3, 2), "Email", font_size=8, color=DGRAY)

    # Add bottom border under row 0 col 0 (signature line)
    _add_bottom_border(st.cell(0, 0), "000000", 6)

    for col_idx, w in enumerate([Cm(5.5), Cm(5.5), Cm(5.5)]):
        for row_idx in range(4):
            st.cell(row_idx, col_idx).width = w

    doc.add_paragraph()

    # ── 8. FOOTER ─────────────────────────────────────────────────────────────
    _add_hr(doc)
    _add_para(
        doc,
        f"Certificate of Analysis — {coa.product_name} — Lot: {coa.lot_number} — "
        f"Issued: {date.today().strftime('%Y-%m-%d')} — "
        "Results relate only to the sample as received. "
        "This document shall not be reproduced except in full without written approval.",
        font_size=7.5, color=DGRAY, align=WD_ALIGN_PARAGRAPH.CENTER,
    )

    doc.save(output_path)
