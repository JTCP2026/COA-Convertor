"""
pdf_generator.py
COA PDF — matches Navi Nature's standard layout:
  2-col header (logo | contact+address) → product info grid → COA title →
  bordered test-results table (4 cols, category bold rows) → signature block
"""
from __future__ import annotations
import os
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

from core.coa_model import COADocument, PassFail, TestCategory, build_display_rows, fit_scale

BLACK = colors.black
DGRAY = colors.HexColor("#555555")
LGRAY = colors.HexColor("#F0F0F0")
MGRAY = colors.HexColor("#DDDDDD")
GREEN = colors.HexColor("#1A7A4A")
RED   = colors.HexColor("#C0392B")
NAVY  = colors.HexColor("#0D2B55")

_CATEGORY_LABELS = {
    TestCategory.PHYSICAL.value:        "Physical Characteristics",
    TestCategory.CHEMICAL.value:        "Chemical Properties",
    TestCategory.MICROBIOLOGICAL.value: "Microbiological Data",
    TestCategory.OTHER.value:           "Other",
}


def _S(scale: float = 1.0):
    def sz(v):
        return v * scale

    return {
        # Header area
        "co_name":   ParagraphStyle("co_name",  fontSize=sz(16), leading=sz(20), fontName="Helvetica-Bold",
                                    alignment=TA_CENTER, textColor=BLACK),
        "co_addr":   ParagraphStyle("co_addr",  fontSize=sz(9),  leading=sz(13), fontName="Helvetica",
                                    alignment=TA_CENTER, textColor=DGRAY),
        "hdr_small": ParagraphStyle("hdr_sm",   fontSize=sz(8),  leading=sz(11), fontName="Helvetica",
                                    textColor=DGRAY),
        # Shipment info block
        "info_lbl":  ParagraphStyle("ilbl",     fontSize=sz(9),  leading=sz(13), fontName="Helvetica-Bold",
                                    textColor=BLACK),
        "info_val":  ParagraphStyle("ival",     fontSize=sz(9),  leading=sz(13), fontName="Helvetica",
                                    textColor=BLACK),
        # COA title
        "coa_title": ParagraphStyle("ct",       fontSize=sz(13), leading=sz(17), fontName="Helvetica-Bold",
                                    alignment=TA_CENTER, textColor=BLACK),
        "coa_sub":   ParagraphStyle("cs",       fontSize=sz(9),  leading=sz(13), fontName="Helvetica-Oblique",
                                    alignment=TA_CENTER, textColor=DGRAY),
        # Table headers (underlined look via TableStyle)
        "t_hdr":     ParagraphStyle("thdr",     fontSize=sz(9),  leading=sz(12), fontName="Helvetica-Bold",
                                    textColor=BLACK),
        # Category row
        "t_cat":     ParagraphStyle("tcat",     fontSize=sz(9),  leading=sz(12), fontName="Helvetica-Bold",
                                    textColor=BLACK),
        # Data cells
        "t_cell":    ParagraphStyle("tcell",    fontSize=sz(8.5),leading=sz(11), fontName="Helvetica",
                                    textColor=BLACK),
        "t_result_pass": ParagraphStyle("trp",  fontSize=sz(8.5),leading=sz(11), fontName="Helvetica",
                                        textColor=GREEN),
        "t_result_fail": ParagraphStyle("trf",  fontSize=sz(8.5),leading=sz(11), fontName="Helvetica",
                                        textColor=RED),
        # QC / signature
        "qc_text":   ParagraphStyle("qct",      fontSize=sz(8.5),leading=sz(13), fontName="Helvetica-Oblique",
                                    alignment=TA_CENTER, textColor=DGRAY),
        "sig_lbl":   ParagraphStyle("slbl",     fontSize=sz(8),  leading=sz(10), fontName="Helvetica",
                                    textColor=DGRAY),
        "sig_val":   ParagraphStyle("sval",     fontSize=sz(9),  leading=sz(12), fontName="Helvetica",
                                    textColor=BLACK),
        "sig_name":  ParagraphStyle("snam",     fontSize=sz(9),  leading=sz(12), fontName="Helvetica-Bold",
                                    textColor=BLACK),
        "footer":    ParagraphStyle("ft",       fontSize=sz(7),  leading=sz(10), fontName="Helvetica",
                                    alignment=TA_CENTER, textColor=DGRAY),
    }


def _hr(width="100%", thickness=0.75, color=DGRAY, space_before=3, space_after=3):
    return HRFlowable(width=width, thickness=thickness, color=color,
                      spaceBefore=space_before, spaceAfter=space_after)


def generate_pdf(doc: COADocument, output_path: str) -> None:
    scale = fit_scale(len(doc.test_results))

    W, H = A4
    margin = (18 if scale >= 1.0 else 14) * mm
    usable_w = W - 2 * margin

    pdf = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=margin, bottomMargin=margin,
        title=f"Certificate of Analysis — {doc.product_name}",
        author=doc.receiving_company_name,
    )
    S = _S(scale)
    story = []

    # ── 1. COMPANY HEADER ─────────────────────────────────────────────────────
    # Two-column: [logo] | [company contact + address]
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
        # Left: logo (or company name if no logo). Right: contact + address.
        left_cell = []
        if doc.receiving_company_logo_path and os.path.exists(doc.receiving_company_logo_path):
            try:
                left_cell.append(RLImage(doc.receiving_company_logo_path,
                                         width=45 * mm, height=20 * mm,
                                         kind="proportional"))
            except Exception:
                pass
        if not left_cell:
            left_cell.append(Paragraph(doc.receiving_company_name or "", S["co_name"]))

        right_lines = []
        if doc.receiving_company_phone:
            right_lines.append(Paragraph(f"Tel: {doc.receiving_company_phone}", S["hdr_small"]))
        if doc.receiving_company_website:
            right_lines.append(Paragraph(f"Web: {doc.receiving_company_website}", S["hdr_small"]))
        addr_parts = (doc.receiving_company_address or "").split("\n")
        addr_joined = ", ".join(p.strip() for p in addr_parts if p.strip())
        if addr_joined:
            right_lines.append(Paragraph(f"Add: {addr_joined}", S["hdr_small"]))

        hdr_data = [[left_cell, right_lines or [Paragraph("", S["hdr_small"])]]]
        hdr_t = Table(hdr_data, colWidths=[usable_w * 0.4, usable_w * 0.6])
        hdr_t.setStyle(TableStyle([
            ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN",       (0, 0), (0, 0),   "LEFT"),
            ("ALIGN",       (1, 0), (1, 0),   "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING",(0, 0), (-1, -1), 4),
        ]))
        story.append(hdr_t)
        story.append(_hr(color=MGRAY, thickness=0.5, space_before=4, space_after=4))

    # ── 2. (removed — no supplier/subject company block) ─────────────────────

    # ── 4. COA TITLE ─────────────────────────────────────────────────────────
    story.append(Paragraph("CERTIFICATE OF ANALYSIS", S["coa_title"]))
    story.append(Spacer(1, 3 * mm * scale))

    # ── 3. PRODUCT INFO GRID ──────────────────────────────────────────────────
    # 2 columns x N rows of (label, value) pairs, mirroring the company's
    # standard layout: Product Name/Batch No., Botanical Name/Production Date,
    # Plant Part/Analysis Date, Country of Origin/Re-test Date.
    grid_pairs = [
        (("Product name", doc.product_name), ("Batch no.", doc.lot_number)),
        (("Botanical name", doc.botanical_name), ("Production date", doc.manufacturing_date)),
        (("Plant part", doc.plant_part), ("Analysis date", doc.date_of_analysis)),
        (("Country of origin", doc.manufacturer_country), ("Re-test date", doc.retest_date)),
    ]
    grid_data = []
    for (l1, v1), (l2, v2) in grid_pairs:
        if not (v1 and v1.strip()) and not (v2 and v2.strip()):
            continue
        grid_data.append([
            Paragraph(l1, S["info_lbl"]), Paragraph(v1 or "", S["info_val"]),
            Paragraph(l2, S["info_lbl"]), Paragraph(v2 or "", S["info_val"]),
        ])
    if grid_data:
        col_w4 = [usable_w * 0.16, usable_w * 0.34, usable_w * 0.16, usable_w * 0.34]
        grid_t = Table(grid_data, colWidths=col_w4)
        grid_t.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
            ("TOPPADDING",    (0, 0), (-1, -1), 2 * scale),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * scale),
        ]))
        story.append(grid_t)
    story.append(Spacer(1, 5 * mm * scale))

    # ── 5. TEST RESULTS TABLE ────────────────────────────────────────────────
    if doc.test_results:
        display_rows = build_display_rows(doc.test_results, _CATEGORY_LABELS)

        # 4 columns: Analysis Item | Specification | Result | Analysis Test Method
        col_w = [usable_w * 0.28, usable_w * 0.24, usable_w * 0.24, usable_w * 0.24]

        # Header row
        hdrs = ["Analysis Item", "Specification", "Result", "Analysis Test Method"]
        table_data = [[Paragraph(h, S["t_hdr"]) for h in hdrs]]
        row_styles: list[tuple] = [
            # Underline the header row
            ("LINEBELOW",     (0, 0), (-1, 0), 0.8, BLACK),
            ("LINEABOVE",     (0, 0), (-1, 0), 0.4, MGRAY),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 3),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
            ("TOPPADDING",    (0, 0), (-1, -1), 3 * scale),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * scale),
            ("GRID",          (0, 0), (-1, -1), 0.4, MGRAY),
        ]

        row_idx = 1
        for kind, payload in display_rows:
            if kind == "band":
                table_data.append([Paragraph(payload, S["t_cat"])] + ["", "", ""])
                row_styles += [
                    ("SPAN",          (0, row_idx), (3, row_idx)),
                    ("BACKGROUND",    (0, row_idx), (-1, row_idx), LGRAY),
                    ("TOPPADDING",    (0, row_idx), (-1, row_idx), 4 * scale),
                    ("BOTTOMPADDING", (0, row_idx), (-1, row_idx), 4 * scale),
                    ("LINEABOVE",     (0, row_idx), (-1, row_idx), 0.3, MGRAY),
                ]
            else:
                tr = payload
                result_text = f"{tr.result} {tr.unit}".strip() if tr.unit else (tr.result or "")
                result_style = (
                    S["t_result_pass"] if tr.pass_fail == PassFail.PASS.value
                    else S["t_result_fail"] if tr.pass_fail == PassFail.FAIL.value
                    else S["t_cell"]
                )
                table_data.append([
                    Paragraph(tr.test_name or "", S["t_cell"]),
                    Paragraph(tr.specification or "", S["t_cell"]),
                    Paragraph(result_text, result_style),
                    Paragraph(tr.method or "", S["t_cell"]),
                ])
                row_styles.append(("LINEBELOW", (0, row_idx), (-1, row_idx), 0.2, MGRAY))
            row_idx += 1

        tbl = Table(table_data, colWidths=col_w, repeatRows=1)
        tbl.setStyle(TableStyle(row_styles))
        story.append(tbl)
    else:
        story.append(Paragraph("No test results recorded.", S["t_cell"]))

    story.append(Spacer(1, 8 * mm * scale))

    # ── 7. SIGNATURE BLOCK ────────────────────────────────────────────────────
    sig_date = doc.signature_date or date.today().strftime("%Y-%m-%d")
    story.append(Paragraph("Approved by QC Supervisor", S["sig_lbl"]))
    story.append(Spacer(1, 2 * mm * scale))
    story.append(Paragraph(sig_date, S["sig_val"]))

    # ── 8. FOOTER ─────────────────────────────────────────────────────────────
    # A true page footer (drawn via canvas on every page at a fixed position),
    # not a flowable in `story` — so it stays pinned to the bottom of each
    # page even if the body overflows onto page 2+, instead of being part of
    # whatever page the body content happens to end on.
    footer_line1 = (
        f"Certificate of Analysis — {doc.product_name} — Lot: {doc.lot_number} — "
        f"Issued: {date.today().strftime('%m/%d/%Y')}"
    )
    footer_line2 = (
        "Results relate only to the sample as received. "
        "This document shall not be reproduced except in full without written approval."
    )

    def _draw_footer(canvas_obj, _template):
        canvas_obj.saveState()
        canvas_obj.setFont("Helvetica", 7 * scale)
        canvas_obj.setFillColor(DGRAY)
        canvas_obj.setStrokeColor(MGRAY)
        canvas_obj.setLineWidth(0.4)
        line_y = margin - 4 * mm
        canvas_obj.line(margin, line_y, W - margin, line_y)
        canvas_obj.drawCentredString(W / 2, margin - 8 * mm, footer_line1)
        canvas_obj.drawCentredString(W / 2, margin - 12 * mm, footer_line2)
        canvas_obj.restoreState()

    pdf.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
