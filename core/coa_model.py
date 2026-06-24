from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class PassFail(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NT = "N/T"  # Not Tested


class Disposition(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    CONDITIONAL = "CONDITIONALLY RELEASED"
    PENDING = "PENDING REVIEW"


class TestCategory(str, Enum):
    PHYSICAL = "Physical"
    CHEMICAL = "Chemical"
    MICROBIOLOGICAL = "Microbiological"
    OTHER = "Other"


@dataclass
class TestResult:
    test_name: str = ""
    category: str = TestCategory.PHYSICAL.value
    # Raw category banner text as it appeared in the supplier's own document
    # (e.g. "Organoleptic properties"). Optional — when present, generators
    # display this verbatim instead of the generic `category` bucket label.
    category_label: str = ""
    specification: str = ""
    result: str = ""
    unit: str = ""
    method: str = ""
    pass_fail: str = PassFail.PASS.value


@dataclass
class COADocument:
    # Header / Identity
    certificate_number: str = ""
    date_of_analysis: str = ""
    product_name: str = ""
    internal_item_code: str = ""
    supplier_product_code: str = ""
    lot_number: str = ""
    # Raw batch no. as it appeared in the supplier's document — preserved
    # separately so switching product_category away from Botanical can
    # restore it (lot_number itself may get overwritten by the generated
    # Botanical batch number).
    supplier_batch_number: str = ""
    quantity_received: str = ""
    purchase_order_number: str = ""

    # Manufacturer / Supplier
    manufacturer_name: str = ""
    manufacturer_address: str = ""
    manufacturer_country: str = ""
    supplier_name: str = ""

    # Product classification (drives batch-number generation logic)
    product_category: str = ""  # Botanical / Vitamins / Amino Acids / Mineral
    botanical_name: str = ""
    plant_part: str = ""

    # Dates
    manufacturing_date: str = ""
    expiry_date: str = ""
    retest_date: str = ""
    date_received: str = ""

    # Test Results
    test_results: list[TestResult] = field(default_factory=list)

    # Release / QC
    overall_disposition: str = Disposition.PASS.value
    qc_release_statement: str = ""
    authorised_signatory_name: str = ""
    authorised_signatory_title: str = ""
    signature_date: str = ""

    # Receiving company (from config — populated at generation time)
    receiving_company_name: str = ""
    receiving_company_address: str = ""
    receiving_company_phone: str = ""
    receiving_company_website: str = ""
    receiving_company_logo_path: str = ""
    receiving_company_header_path: str = ""

    REQUIRED_FIELDS = [
        "product_name",
        "lot_number",
        "date_of_analysis",
    ]

    def validate(self) -> list[str]:
        """Return list of missing required field names."""
        missing = []
        for f in self.REQUIRED_FIELDS:
            if not getattr(self, f, "").strip():
                missing.append(f)
        return missing


def build_display_rows(
    test_results: list[TestResult],
    category_labels: dict[str, str],
) -> list[tuple[str, object]]:
    """
    Build a flat render sequence for the test-results table: a band row
    whenever the category label changes from the previous row, followed by
    the data row. Rows with no category at all (both `category` and
    `category_label` left blank — e.g. a supplier's unlabelled "Ratio" row)
    render with no preceding band. Rows using the legacy `category` enum
    (the common case for manually-entered results) still get a band from
    `category_labels`.

    Returns a list of ("band", label_str) and ("row", TestResult) tuples.
    """
    rows: list[tuple[str, object]] = []
    prev_label: str | None = None
    for tr in test_results:
        if tr.category_label:
            label = tr.category_label
        elif tr.category:
            label = category_labels.get(tr.category, tr.category)
        else:
            label = ""
        label = (label or "").strip()
        if label and label != prev_label:
            rows.append(("band", label))
            prev_label = label
        elif not label:
            prev_label = None
        rows.append(("row", tr))
    return rows


def fit_scale(n_rows: int) -> float:
    """Best-effort scale factor (shared by both generators) to keep the COA
    on a single page as the test-results row count grows. Not a guaranteed
    fit — extremely long tables may still overflow even at the floor scale."""
    if n_rows <= 18:
        return 1.0
    if n_rows <= 25:
        return 0.92
    if n_rows <= 32:
        return 0.85
    if n_rows <= 40:
        return 0.78
    return 0.75


# Maps field name → human-readable label
FIELD_LABELS: dict[str, str] = {
    "certificate_number": "Certificate No.",
    "date_of_analysis": "Date of Analysis",
    "product_name": "Product Name",
    "internal_item_code": "Internal Item Code",
    "supplier_product_code": "Supplier Product Code",
    "lot_number": "Lot / Batch No.",
    "quantity_received": "Quantity Received",
    "purchase_order_number": "Purchase Order No.",
    "manufacturer_name": "Manufacturer",
    "manufacturer_address": "Manufacturer Address",
    "manufacturer_country": "Country of Origin",
    "supplier_name": "Supplier Name",
    "product_category": "Product Category",
    "botanical_name": "Botanical Name",
    "plant_part": "Plant Part",
    "manufacturing_date": "Manufacturing Date",
    "expiry_date": "Expiry Date",
    "retest_date": "Retest Date",
    "date_received": "Date Received",
    "overall_disposition": "Overall Disposition",
    "qc_release_statement": "QC Release Statement",
    "authorised_signatory_name": "Authorised Signatory",
    "authorised_signatory_title": "Title",
    "signature_date": "Signature Date",
}
