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
    quantity_received: str = ""
    purchase_order_number: str = ""

    # Manufacturer / Supplier
    manufacturer_name: str = ""
    manufacturer_address: str = ""
    manufacturer_country: str = ""
    supplier_name: str = ""

    # Dates
    manufacturing_date: str = ""
    expiry_date: str = ""
    retest_date: str = ""
    date_received: str = ""

    # Test Results
    test_results: list[TestResult] = field(default_factory=list)

    # Release / QC
    overall_disposition: str = Disposition.PENDING.value
    qc_release_statement: str = ""
    authorised_signatory_name: str = ""
    authorised_signatory_title: str = ""
    signature_date: str = ""

    # Receiving company (from config — populated at generation time)
    receiving_company_name: str = ""
    receiving_company_address: str = ""
    receiving_company_logo_path: str = ""
    receiving_company_header_path: str = ""

    REQUIRED_FIELDS = [
        "product_name",
        "lot_number",
        "date_of_analysis",
        "manufacturer_name",
    ]

    def validate(self) -> list[str]:
        """Return list of missing required field names."""
        missing = []
        for f in self.REQUIRED_FIELDS:
            if not getattr(self, f, "").strip():
                missing.append(f)
        return missing


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
