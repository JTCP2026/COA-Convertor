"""
pdf_generator.py
COA PDF — matches industry-standard layout:
  3-col header → company block → shipment info → COA title →
  open test-results table (4 cols, category bold rows) → QC statement → signature block
"""
from __future__ import annotations
import os
from collections import defaultdict
from datetime import date
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable, Image as RLImage,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from core.coa_model import COADocument, PassFail, TestCategory

BLACK = colors.black
DGRAY = colors.HexColor("#555555")
LGRAY = colors.HexColor("#F0F0F0")
MGRAY = colors.HexColor("#DDDDDD")
GREEN = colors.HexColor("#1A7A4A")
RED   = colors.HexColor("#C0392B")
NAVY  = colors.HexColor("#0D2B55")

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


def _S():
    return {
        # Header area
        "co_name":   ParagraphStyle("co_name",  fontSize=16, leading=20, fontName="Helvetica-Bold",
                                    alignment=TA_CENTER, textColor=BLACK),
        "co_addr":   ParagraphStyle("co_addr",  fontSize=9,  leading=13, fontName="Helvetica",
                                    alignment=TA_CENTER, textColor=DGRAY),
        "hdr_small": ParagraphStyle("hdr_sm",   fontSize=8,  leading=11, fontName="Helvetica",
                                    textColor=DGRAY),
        # Shipment info block
        "info_lbl":  ParagraphStyle("ilbl",     fontSize=9,  leading=13, fontName="Helvetica-Bold",
                                    textColor=BLACK),
        "info_val":  ParagraphStyle("ival",     fontSize=9,  leading=13, fontName="Helvetica",
                                    textColor=BLACK),
        # COA title
        "coa_title": ParagraphStyle("ct",       fontSize=13, leading=17, fontName="Helvetica-Bold",
                                    alignment=TA_CENTER, textColor=BLACK),
        "coa_sub":   ParagraphStyle("cs",       fontSize=9,  leading=13, fontName="Helvetica-Oblique",
                                    alignment=TA_CENTER, textColor=DGRAY),
        # Table headers (underlined look via TableStyle)
        "t_hdr":     ParagraphStyle("thdr",     fontSize=9,  leading=12, fontName="Helvetica-Bold",
                                    textColor=BLACK),
        # Category row
        "t_cat":     ParagraphStyle("tcat",     fontSize=9,  leading=12, fontName="Helvetica-Bold",
                                    textColor=BLACK),
        # Data cells
        "t_cell":    ParagraphStyle("tcell",    fontSize=8.5,leading=11, fontName="Helvetica",
                                    textColor=BLACK),
        "t_result_pass": ParagraphStyle("trp",  fontSize=8.5,leading=11, fontName="Helvetica",
                                        textColor=GREEN),
        "t_result_fail": ParagraphStyle("trf",  fontSize=8.5,leading=11, fontName="Helvetica",
                                        textColor=RED),
        # QC / signature
        "qc_text":   ParagraphStyle("qct",      fontSize=8.5,leading=13, fontName="Helvetica-Oblique",
                                    alignment=TA_CENTER, textColor=DGRAY),
        "sig_lbl":   ParagraphStyle("slbl",     fontSize=8,  leading=10, fontName="Helvetica",
                                    textColor=DGRAY),
        "sig_val":   ParagraphStyle("sval",     fontSize=9,  leading=12, fontName="Helvetica",
                                    textColor=BLACK),
        "sig_name":  ParagraphStyle("snam",     fontSize=9,  leading=12, fontName="Helvetica-Bold",
                                    textColor=BLACK),
        "footer":    ParagraphStyle("ft",       fontSize=7,  leading=10, fontName="Helvetica",
                                    alignment=TA_CENTER, textColor=DGRAY),
    }


def _hr(width="100%", thickness=0.75, color=DGRAY, space_before=3, space_after=3):
    return HRFlowable(width=width, thickness=thickness, color=color,
                      spaceBefore=space_before, spaceAfter=space_after)


def generate_pdf(doc: COADocument, output_path: str) -> None:
    W, H = A4
    margin = 18 * mm
    usable_w = W - 2 * margin

    pdf = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=margin, bottomMargin=margin,
        title=f"Certificate of Analysis — {doc.product_name}",
        author=doc.receiving_company_name,
    )
    S = _S()
    story = []

    # ── 1. COMPANY HEADER ─────────────────────────────────────────────────────
    # Three-column: [contact info | logo/name | address]
    if doc.receiving_company_header_path and os.path.exists(doc.receiving_company_header_path):
        # Full-width custom header image
        try:
            from PIL import Image as PILImage
            with PILImage.open(doc.receiving_company_header_path) as _im:
                _iw, _ih = _im.size
            aspect = _ih / _iw if _iw else 1
            banner_h = min(usable_w * aspect, 40 * mm)
            story.append(RLImage(doc.receiving_company_header_path,
                                 width=usable_w, height=banner_h))
        except Exception:
            pass
        story.append(_hr(color=MGRAY, space_before=2, space_after=4))
    else:
        # Build 3-column header: left contact | center logo/name | right address
        left_lines = []
        # We put QC signatory contact on the left
        if doc.authorised_signatory_name:
            left_lines.append(Paragraph(doc.authorised_signatory_name, S["hdr_small"]))
        if doc.authorised_signatory_title:
            left_lines.append(Paragraph(doc.authorised_signatory_title, S["hdr_small"]))

        # Center: logo or company name
        center_cell = []
        if doc.receiving_company_logo_path and os.path.exists(doc.receiving_company_logo_path):
            try:
                center_cell.append(RLImage(doc.receiving_company_logo_path,
                                           width=45 * mm, height=20 * mm,
                                           kind="proportional"))
            except Exception:
                pass
        if not center_cell:
            center_cell.append(Paragraph(doc.receiving_company_name or "", S["co_name"]))

        # Right: company address
        right_lines = []
        if doc.receiving_company_name:
            right_lines.append(Paragraph(f"<b>{doc.receiving_company_name}</b>", S["hdr_small"]))
        addr_parts = (doc.receiving_company_address or "").split("\n")
        for part in addr_parts:
            if part.strip():
                right_lines.append(Paragraph(part.strip(), S["hdr_small"]))

        hdr_data = [[left_lines or [""], center_cell, right_lines or [""]]]
        hdr_t = Table(hdr_data, colWidths=[usable_w * 0.28, usable_w * 0.44, usable_w * 0.28])
        hdr_t.setStyle(TableStyle([
            ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN",       (0, 0), (0, 0),   "LEFT"),
            ("ALIGN",       (1, 0), (1, 0),   "CENTER"),
            ("ALIGN",       (2, 0), (2, 0),   "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING",(0, 0), (-1, -1), 4),
        ]))
        story.append(hdr_t)
        story.append(_hr(color=MGRAY, thickness=0.5, space_before=4, space_after=4))

    # ── 2. SUPPLIER / SUBJECT COMPANY BLOCK (centered, large) ────────────────
    supplier_name = doc.supplier_name or doc.manufacturer_name
    if supplier_name:
        story.append(Paragraph(supplier_name, S["co_name"]))
    if doc.manufacturer_address:
        for line in doc.manufacturer_address.split("\n"):
            if line.strip():
                story.append(Paragraph(line.strip(), S["co_addr"]))
    story.append(Spacer(1, 4 * mm))

    # ── 3. SHIPMENT / PRODUCT INFO BLOCK ─────────────────────────────────────
    # Bold ALL-CAPS label | value pairs (no box, left aligned)
    info_rows = [
        ("SUPPLIER NAME & LOCATION",
         f"{supplier_name or '—'}"
         + (f", {doc.manufacturer_address.replace(chr(10), ', ')}" if doc.manufacturer_address else "")),
        ("INGREDIENT NAME",    doc.product_name),
        ("INGREDIENT NUMBER",  doc.internal_item_code or doc.supplier_product_code),
        ("PURCHASE ORDER #",   doc.purchase_order_number),
        ("DATE OF ANALYSIS",   doc.date_of_analysis),
        ("DATE OF SHIPMENT",   doc.manufacturing_date or doc.date_received),
        ("EXPIRY / RETEST DATE", doc.expiry_date or doc.retest_date),
        ("CERTIFICATE NO.",    doc.certificate_number),
        ("LOT NUMBER",         doc.lot_number),
    ]
    # Only include rows that have values
    info_rows = [(lbl, val) for lbl, val in info_rows if val and val.strip()]

    lbl_w = usable_w * 0.30
    val_w = usable_w * 0.70
    info_data = [
        [Paragraph(f"{lbl}:", S["info_lbl"]), Paragraph(str(val), S["info_val"])]
        for lbl, val in info_rows
    ]
    if info_data:
        info_t = Table(info_data, colWidths=[lbl_w, val_w])
        info_t.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
            ("TOPPADDING",    (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(info_t)
    story.append(Spacer(1, 4 * mm))
    story.append(_hr(color=DGRAY, thickness=0.8, space_before=2, space_after=5))

    # ── 4. COA TITLE ─────────────────────────────────────────────────────────
    story.append(Paragraph("CERTIFICATE OF ANALYSIS", S["coa_title"]))
    story.append(Paragraph("Analytical Data for This Shipment", S["coa_sub"]))
    story.append(Spacer(1, 5 * mm))

    # ── 5. TEST RESULTS TABLE ────────────────────────────────────────────────
    if doc.test_results:
        grouped: dict[str, list] = defaultdict(list)
        for tr in doc.test_results:
            cat = tr.category if tr.category in _CATEGORY_LABELS else TestCategory.OTHER.value
            grouped[cat].append(tr)

        # 4 columns: Attribute | Method Reference | Specification | Test Results
        col_w = [usable_w * 0.28, usable_w * 0.24, usable_w * 0.24, usable_w * 0.24]

        # Header row
        hdrs = ["Attribute", "Method Reference", "Specification", "Test Results"]
        table_data = [[Paragraph(h, S["t_hdr"]) for h in hdrs]]
        row_styles: list[tuple] = [
            # Underline the header row
            ("LINEBELOW",     (0, 0), (-1, 0), 0.8, BLACK),
            ("LINEABOVE",     (0, 0), (-1, 0), 0.4, MGRAY),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 3),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]

        row_idx = 1
        for cat in _CATEGORY_ORDER:
            if not grouped.get(cat):
                continue
            # Category label row (bold, spanning all cols, light shading)
            table_data.append([Paragraph(_CATEGORY_LABELS[cat], S["t_cat"])] + ["", "", ""])
            row_styles += [
                ("SPAN",          (0, row_idx), (3, row_idx)),
                ("BACKGROUND",    (0, row_idx), (-1, row_idx), LGRAY),
                ("TOPPADDING",    (0, row_idx), (-1, row_idx), 4),
                ("BOTTOMPADDING", (0, row_idx), (-1, row_idx), 4),
                ("LINEABOVE",     (0, row_idx), (-1, row_idx), 0.3, MGRAY),
            ]
            row_idx += 1

            for tr in grouped[cat]:
                # Combine result + unit
                result_text = f"{tr.result} {tr.unit}".strip() if tr.unit else (tr.result or "")
                result_style = (
                    S["t_result_pass"] if tr.pass_fail == PassFail.PASS.value
                    else S["t_result_fail"] if tr.pass_fail == PassFail.FAIL.value
                    else S["t_cell"]
                )
                row = [
                    Paragraph(tr.test_name or "", S["t_cell"]),
                    Paragraph(tr.method or "", S["t_cell"]),
                    Paragraph(tr.specification or "", S["t_cell"]),
                    Paragraph(result_text, result_style),
                ]
                table_data.append(row)
                row_styles.append(("LINEBELOW", (0, row_idx), (-1, row_idx), 0.2, MGRAY))
                row_idx += 1

        tbl = Table(table_data, colWidths=col_w, repeatRows=1)
        tbl.setStyle(TableStyle(row_styles))
        story.append(tbl)
    else:
        story.append(Paragraph("No test results recorded.", S["t_cell"]))

    story.append(Spacer(1, 10 * mm))
    story.append(_hr(color=DGRAY, thickness=0.8, space_before=2, space_after=5))

    # ── 6. QC RELEASE STATEMENT ───────────────────────────────────────────────
    story.append(Paragraph(
        doc.qc_release_statement or
        "This item is regularly tested and meets all requirements defined by the appropriate "
        "current ingredient specification. This item is manufactured, packaged, stored, and "
        "shipped in accordance with Good Manufacturing Practices and under modern sanitary conditions.",
        S["qc_text"]
    ))
    story.append(Spacer(1, 4 * mm))
    story.append(_hr(color=DGRAY, thickness=0.8, space_before=2, space_after=5))

    # ── 7. SIGNATURE BLOCK ────────────────────────────────────────────────────
    sig_date = doc.signature_date or date.today().strftime("%B %d %Y")

    sig_data = [
        # Row 0: values (signature line | title | date)
        [Paragraph("", S["sig_val"]),                              # signature space
         Paragraph(doc.authorised_signatory_title or "Quality Control Manager", S["sig_val"]),
         Paragraph(sig_date, S["sig_val"])],
        # Row 1: labels under the above
        [Paragraph("Name", S["sig_lbl"]),
         Paragraph("Title", S["sig_lbl"]),
         Paragraph("Date", S["sig_lbl"])],
        # Row 2: full name | contact info | email
        [Paragraph(doc.authorised_signatory_name or "", S["sig_name"]),
         Paragraph("", S["sig_val"]),
         Paragraph("", S["sig_val"])],
        # Row 3: labels
        [Paragraph("Printed Name", S["sig_lbl"]),
         Paragraph("Phone Number", S["sig_lbl"]),
         Paragraph("Email", S["sig_lbl"])],
    ]
    cw3 = [usable_w / 3] * 3
    sig_t = Table(sig_data, colWidths=cw3)
    sig_t.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        # Underline name row (row 0) for signature
        ("LINEBELOW",     (0, 0), (0, 0), 0.5, BLACK),
        ("LINEBELOW",     (0, 2), (0, 2), 0.3, MGRAY),
        # Light separator between rows 1 and 2
        ("LINEBELOW",     (0, 1), (-1, 1), 0.5, MGRAY),
    ]))
    story.append(sig_t)

    # ── 8. FOOTER ─────────────────────────────────────────────────────────────
    story.append(Spacer(1, 6 * mm))
    story.append(_hr(color=MGRAY, thickness=0.4, space_before=1, space_after=2))
    story.append(Paragraph(
        f"Certificate of Analysis — {doc.product_name} — Lot: {doc.lot_number} — "
        f"Issued: {date.today().strftime('%Y-%m-%d')} — "
        "Results relate only to the sample as received. "
        "This document shall not be reproduced except in full without written approval.",
        S["footer"],
    ))

    pdf.build(story)
