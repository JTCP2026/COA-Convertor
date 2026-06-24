"""
field_mapper.py
Maps raw extracted text/tables to COADocument fields.
Returns (COADocument, FieldConfidence dict).
"""
from __future__ import annotations
import re
from datetime import datetime
from typing import Any
from dateutil import parser as dateutil_parser
from .coa_model import COADocument, TestResult, PassFail, TestCategory

FieldConfidence = dict[str, float]

# ---------------------------------------------------------------------------
# Keyword pattern registry — each entry: (compiled_regex, capture_group_index)
# ---------------------------------------------------------------------------

def _build(patterns: list[str], flags: int = re.IGNORECASE) -> re.Pattern:
    return re.compile("|".join(patterns), flags)


_LOT = _build([
    r'(?:lot|batch)[\s_-]*(?:no\.?|number|#|id|code)?\s*[:#\-]?\s*([A-Z0-9][A-Z0-9\-_/]{2,19})',
    r'(?:l/n|b/n|ln|bn)\s*[:#\-]?\s*([A-Z0-9][A-Z0-9\-_/]{2,19})',
    r'(?:control|production|reference|ref)[\s_-]*(?:no\.?|number|#)\s*[:#\-]?\s*([A-Z0-9][A-Z0-9\-_/]{2,19})',
    r'(?:批号|批次号|批次|生产批号|出厂批号|检验批号|批编号|批次编码|货批号)\s*[：:＃#\-]?\s*([A-Z0-9一-鿿][A-Z0-9\-_/一-鿿]{2,19})',
])

_DATE_FRAG = (
    r'(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}'
    r'|\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}'
    r'|\d{4}[年/]\d{1,2}[月/]\d{1,2}日?'
    r'|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s\-,\.]+\d{1,2}[\s,\.]+\d{4}'
    r'|\d{8})'
)

_MFG_DATE = _build([
    rf'(?:manufacturing|manufacture|mfg\.?|mfr\.?|production|fabrication|made)[\s_-]*(?:date|dt\.?)?\s*[:#\-]?\s*{_DATE_FRAG}',
    rf'(?:date[\s_-]*(?:of[\s_-]*)?(?:manufacture|manufacturing|production|fabrication))\s*[:#\-]?\s*{_DATE_FRAG}',
    rf'(?:produced[\s_-]*(?:on|date))\s*[:#\-]?\s*{_DATE_FRAG}',
    rf'(?:生产日期|制造日期|出厂日期|生产时间|制造时间|生产年月|出厂年月|制造年月)\s*[：:]\s*{_DATE_FRAG}',
])

_EXP_DATE = _build([
    rf'(?:expiry|expiration|exp\.?|best[\s_-]*before|use[\s_-]*(?:by|before)|best[\s_-]*by|bb[\s_-]*date)[\s_-]*(?:date|dt\.?)?\s*[:#\-]?\s*{_DATE_FRAG}',
    rf'(?:valid[\s_-]*(?:until|through|to|thru)|validity[\s_-]*date|shelf[\s_-]*life[\s_-]*(?:expiry|expiration|until|to))\s*[:#\-]?\s*{_DATE_FRAG}',
    rf'(?:有效期|有效期至|有效日期|失效日期|保质期|最佳使用期限|使用期限|到期日|截止日期|有效期限)\s*[：:至到]?\s*{_DATE_FRAG}',
])

_RETEST_DATE = _build([
    rf'(?:retest|re-test|reanalysis|retesting|next[\s_-]*test|re-evaluation|review)[\s_-]*(?:date|dt\.?)?\s*[:#\-]?\s*{_DATE_FRAG}',
    rf'(?:复验日期|复检日期|重新检验日期|再检验日期|复测日期|下次检验日期)\s*[：:]\s*{_DATE_FRAG}',
])

_PRODUCT_NAME = _build([
    r'(?:product|material|ingredient|substance|item|article|raw[\s_-]*material|commodity)[\s_-]*(?:name|description|desc\.?)?\s*[:#\-]?\s*(.{3,80})',
    r'(?:chemical[\s_-]*name|trade[\s_-]*name|brand[\s_-]*name|specification[\s_-]*name)\s*[:#\-]?\s*(.{3,80})',
    r'(?:品名|产品名称|物料名称|原料名称|品名规格|商品名|化学名|通用名|原材料名称|物质名称|货品名称|项目名称)\s*[：:]\s*(.{2,60})',
])

_MANUFACTURER = _build([
    r'(?:manufacturer|manufactured[\s_-]*by|maker|producer|prepared[\s_-]*by|produced[\s_-]*by|fabricated[\s_-]*by)\s*[:#\-]?\s*(.{3,120})',
    r'(?:manufacturing[\s_-]*site|production[\s_-]*site|plant|facility)\s*[:#\-]?\s*(.{3,120})',
    r'(?:生产商|制造商|生产厂家|生产企业|生产单位|制造厂|生产厂|制造企业|厂家|厂商|生产方|出品方|委托方|受托方)\s*[：:]\s*(.{2,60})',
])

_SUPPLIER_NAME = _build([
    r'(?:supplier|distributed[\s_-]*by|distributor|vendor|seller|sold[\s_-]*by|importer)\s*[:#\-]?\s*(.{3,120})',
    r'(?:供应商|经销商|代理商|进口商|分销商)\s*[：:]\s*(.{2,60})',
])

_CERT_NUMBER = _build([
    r'(?:certificate|cert\.?)[\s_-]*(?:no\.?|number|#)\s*[:#\-]?\s*([A-Z0-9][A-Z0-9\-_/]{1,30})',
    r'(?:coa|c\.o\.a\.)[\s_-]*(?:no\.?|number|#|ref\.?)\s*[:#\-]?\s*([A-Z0-9][A-Z0-9\-_/]{1,30})',
    r'(?:report|analysis|document|doc\.?)[\s_-]*(?:no\.?|number|#)\s*[:#\-]?\s*([A-Z0-9][A-Z0-9\-_/]{1,30})',
    r'(?:ref(?:erence)?[\s_-]*(?:no\.?|#))\s*[:#\-]?\s*([A-Z0-9][A-Z0-9\-_/]{1,30})',
    r'(?:证书编号|证书号|检验报告编号|报告编号|报告号|分析证书号|合格证编号|文件编号)\s*[：:]\s*([A-Z0-9一-鿿][A-Z0-9\-_/一-鿿]{1,30})',
])

_PO_NUMBER = _build([
    r'(?:purchase[\s_-]*order|p\.?o\.?)[\s_-]*(?:no\.?|number|#)?\s*[:#\-]?\s*([A-Z0-9][A-Z0-9\-_/]{1,30})',
    r'(?:采购单号|采购订单|订单号|PO号)\s*[：:]\s*([A-Z0-9一-鿿]{2,30})',
])

_QUANTITY = _build([
    r'(?:quantity|qty\.?|amount|weight|volume|net[\s_-]*weight|gross[\s_-]*weight)[\s_-]*(?:received)?\s*[:#\-]?\s*(\d[\d,\.]*\s*(?:kg|g|mg|lb|lbs|l|ml|L|mL|units?|pcs?|bags?|drums?)?)',
    r'(?:数量|重量|净重|毛重|体积|容量)[\s_-]*(?:收货)?\s*[：:]\s*(\d[\d,\.]*\s*(?:千克|公斤|克|毫克|升|毫升|件|包|桶)?)',
])

_COUNTRY = _build([
    r'(?:country[\s_-]*of[\s_-]*(?:origin|manufacture|manufacturing)|\borigin\b)\s*[:#\-]?\s*([A-Za-z一-鿿]{2,50})',
    r'(?:原产地|原产国|生产国|制造国|产地)\s*[：:]\s*([A-Za-z一-鿿]{2,20})',
])

_PASS_RE = re.compile(
    r'\b(?:pass(?:ed)?|conforms?|complies?|meets?\s*spec(?:ification)?s?|'
    r'within\s*spec(?:ification)?s?|acceptable|approved|satisfactory|合格|符合|通过|达标)\b',
    re.IGNORECASE,
)
_FAIL_RE = re.compile(
    r'\b(?:fail(?:ed)?|does\s*not\s*conform|non[- ]conform(?:ing)?|'
    r'out\s*of\s*spec(?:ification)?|oos|not\s*acceptable|rejected?|unsatisfactory|不合格|不符合|未通过|超标)\b',
    re.IGNORECASE,
)

# Table header keywords for column detection. Kept in sync with
# _TABLE_HEADER_CANDIDATES below so the position-based and table-based
# extraction paths recognize the same set of header-wording variants.
_TABLE_HEADER_KEYWORDS = {
    "test_name": ["test", "parameter", "item", "attribute", "检验项目", "项目", "检测项目", "测试项目", "指标"],
    "specification": ["specification", "spec", "standard", "requirement", "limit", "acceptance criteria", "规格", "标准", "指标", "限度", "质量标准"],
    "result": ["result", "value", "found", "actual", "observed", "结果", "测定值", "实测值", "检测结果"],
    "method": ["method", "procedure", "standard", "reference", "方法", "检验方法", "检测方法", "依据"],
    "pass_fail": ["pass", "fail", "conform", "status", "判定", "结论", "合格"],
    "unit": ["unit", "units", "单位"],
    "category": ["category", "type", "类别", "类型"],
}

# ---------------------------------------------------------------------------
# Shared label-keyword matching — used both by pdf_parser's position-based
# structured extractor (borderless layouts) and by map_from_tables() below
# (ruled-line tables where a product-info grid sits above the test-results
# table within the same pdfplumber table). Keyword-based, not exact-phrase,
# so differently-worded supplier templates still resolve to the right field.
# ---------------------------------------------------------------------------
_GRID_LABEL_KEYWORDS: dict[str, list[str]] = {
    "retest_date": ["re-test date", "retest date", "re test date"],
    "manufacturing_date": ["production date", "manufacturing date", "manufacture date", "mfg date", "date of manufacture"],
    "date_of_analysis": ["analysis date", "date of analysis", "date analyzed"],
    "botanical_name": ["botanical name", "botanical", "plant source"],
    "plant_part": ["plant part", "part used", "used part"],
    "manufacturer_country": ["country of origin", "country", "origin"],
    "lot_number": ["batch number", "batch no", "lot number", "lot no", "batch", "lot"],
    "quantity_received": ["quantity received", "quantity", "qty"],
    "product_name": ["product name", "item name", "ingredient name", "material name"],
}

_TABLE_HEADER_CANDIDATES = [
    {"analysis item", "test item", "test name", "item", "test", "parameter", "attribute"},
    {"specification", "spec", "limit", "standard", "acceptance criteria"},
    {"result", "value", "found", "test result", "results"},
    {"method", "test method", "analysis test method", "procedure", "reference", "analysis method"},
]


def match_grid_label(text: str) -> str | None:
    """Match a header-grid label phrase to a COADocument field name."""
    norm = text.strip().lower().rstrip(".").strip()
    # Section dividers like "Product information" / "Batch information" are
    # not actual label:value lines — exclude them before keyword matching.
    if re.fullmatch(r"[a-z]+\s+information", norm):
        return None
    if re.search(r"product\s*code|item\s*code|\bsku\b", norm):
        return "supplier_product_code"
    for field_name, keywords in _GRID_LABEL_KEYWORDS.items():
        for kw in keywords:
            if re.search(rf"\b{re.escape(kw)}\b", norm):
                return field_name
    return None


def match_header_col(text: str) -> int | None:
    """Return which of the 4 analysis-table header columns this text is, if any."""
    norm = text.strip().lower().rstrip(".").strip()
    for col_i, candidates in enumerate(_TABLE_HEADER_CANDIDATES):
        if norm in candidates:
            return col_i
    return None


def _first_match(pattern: re.Pattern, text: str) -> tuple[str, float]:
    """Return (value, confidence) for first regex match."""
    m = pattern.search(text)
    if not m:
        return "", 0.0
    for g in m.groups():
        if g:
            return g.strip(), 0.75
    return "", 0.0


def generate_batch_number(product_name: str, production_date: str, category: str) -> str:
    """
    Auto-generate the Batch No. for Botanical-category products from the
    product name initials + production date (YYYYMMDD).

    Rule (derived from Navi Nature's existing naming convention):
      - >=3 words  -> first letter of each of the first 3 words (extra words ignored)
      - 2 words    -> first 2 letters of word 1 + first letter of word 2
      - 1 word     -> first 3 letters of that word
    Non-Botanical categories pass the supplier's own batch number through unchanged
    (this function should not be called for those — see caller).
    """
    if category != "Botanical":
        return ""

    words = [w for w in re.split(r"\s+", (product_name or "").strip()) if w]
    if len(words) >= 3:
        acronym = "".join(w[0] for w in words[:3])
    elif len(words) == 2:
        acronym = words[0][:2] + words[1][0]
    elif len(words) == 1:
        acronym = words[0][:3]
    else:
        acronym = ""
    acronym = acronym.upper()

    date_digits = _date_to_yyyymmdd(production_date)

    return f"{acronym}{date_digits}"


_MONTH_NAME_RE = re.compile(
    r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b', re.IGNORECASE
)


def _parse_date_obj(raw: str) -> datetime | None:
    """
    Parse a date string in any common format, resolving day/month ambiguity
    sensibly:
      1. Unambiguous ISO YYYY-MM-DD / YYYY/MM/DD parsed directly (no guessing)
      2. Formats with an English month name are unambiguous regardless of
         day/month order (e.g. "Jan-14-2025", "Jan. 14 2025")
      3. Purely numeric dates (e.g. "03/04/2024") are ambiguous — try US
         (month-first) first, falling back to day-first if that's invalid
         (e.g. the first number is > 12, so it can't be a month)
    """
    raw = (raw or "").strip()
    if not raw:
        return None

    m = re.match(r'^(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})$', raw)
    if m:
        try:
            dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            if 1990 <= dt.year <= 2050:
                return dt
        except ValueError:
            pass

    if _MONTH_NAME_RE.search(raw):
        try:
            dt = dateutil_parser.parse(raw)
            if 1990 <= dt.year <= 2050:
                return dt
        except Exception:
            pass
        return None

    for dayfirst in (False, True):
        try:
            dt = dateutil_parser.parse(raw, dayfirst=dayfirst)
            if 1990 <= dt.year <= 2050:
                return dt
        except Exception:
            continue
    return None


def _date_to_yyyymmdd(raw: str) -> str:
    """Used for batch-number generation — independent of the display format."""
    dt = _parse_date_obj(raw)
    if dt:
        return dt.strftime("%Y%m%d")
    return re.sub(r"[^0-9]", "", raw or "")


def _parse_date(raw: str) -> str:
    """Normalise any date string to US format MM/DD/YYYY. Returns the
    original string unchanged on failure."""
    dt = _parse_date_obj(raw)
    if dt:
        return dt.strftime("%m/%d/%Y")
    return (raw or "").strip()


def _score_header_row(cells: list[str]) -> dict[str, int]:
    """Return column index mapping field → col index based on header keywords."""
    mapping: dict[str, int] = {}
    for col_i, cell in enumerate(cells):
        cell_lower = cell.lower().strip()
        for field_key, keywords in _TABLE_HEADER_KEYWORDS.items():
            if field_key not in mapping:
                for kw in keywords:
                    if kw in cell_lower:
                        mapping[field_key] = col_i
                        break
    return mapping


def _infer_pass_fail(value: str) -> str:
    if _PASS_RE.search(value):
        return PassFail.PASS.value
    if _FAIL_RE.search(value):
        return PassFail.FAIL.value
    return PassFail.PASS.value


def _detect_category(test_name: str) -> str:
    name_lower = test_name.lower()
    microbio_kw = ["microbial", "microbiological", "bacteria", "yeast", "mold", "mould",
                   "coliform", "ecoli", "e.coli", "salmonella", "cfu", "ufc",
                   "菌", "微生物", "大肠", "霉菌", "酵母"]
    chem_kw = ["assay", "purity", "heavy metal", "arsenic", "lead", "mercury", "cadmium",
               "moisture", "water", "ph", "acid", "alkaline", "solubility", "residue",
               "chloride", "sulfate", "nitrate", "peroxide", "含量", "纯度", "重金属",
               "水分", "灰分", "酸值", "过氧化值"]
    for kw in microbio_kw:
        if kw in name_lower:
            return TestCategory.MICROBIOLOGICAL.value
    for kw in chem_kw:
        if kw in name_lower:
            return TestCategory.CHEMICAL.value
    return TestCategory.PHYSICAL.value


def _fix_concatenated_words(s: str) -> str:
    """pdfplumber sometimes drops the space between words when reconstructing
    cell text (e.g. "CordycepsMilitaris", "YellowBrown Powder"). Insert a
    space at lowercase->uppercase boundaries to undo it. All-caps text
    (abbreviations like "USP", "TLC") has no such boundary and is untouched."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)


def map_from_tables(tables: list[list[list[str]]]) -> tuple[list[TestResult], float, dict[str, str]]:
    """
    Extract TestResult list from structured (pdfplumber) tables. The real
    header row is located anywhere in the table — not assumed to be row 0 —
    because some supplier templates put a product-info grid (Product Name /
    Batch / ...) inside the very same ruled-line table, above the test
    header row. Rows before the header are parsed as that grid (label/value
    pairs); rows after are the test-result data, with single-cell rows
    treated as category banners (category_label) rather than fake results.

    Returns (results, confidence, header_fields).
    """
    results: list[TestResult] = []
    header_fields: dict[str, str] = {}
    best_conf = 0.0

    for table in tables:
        if len(table) < 2:
            continue

        # Require >=2 matched columns before accepting a row as the real
        # header — a single keyword can false-positive (e.g. "Retest Date:"
        # contains the substring "test", which alone would wrongly look
        # like a test_name column).
        header_idx = None
        col_map: dict[str, int] = {}
        for i, row in enumerate(table):
            cells = [str(c) if c else "" for c in row]
            candidate_map = _score_header_row(cells)
            if len(candidate_map) >= 2 and ("test_name" in candidate_map or "result" in candidate_map):
                header_idx = i
                col_map = candidate_map
                break
        if header_idx is None:
            continue

        conf = 0.95 if len(col_map) >= 3 else 0.70
        best_conf = max(best_conf, conf)

        # Rows before the header: a product-info grid, if present.
        for row in table[:header_idx]:
            cells = [_fix_concatenated_words(str(c).strip()) if c else "" for c in row]
            n = len(cells)
            pairs = [(0, 1), (2, 3)] if n >= 4 else ([(0, 1)] if n >= 2 else [])
            for label_i, value_i in pairs:
                field_name = match_grid_label(cells[label_i])
                if field_name and cells[value_i]:
                    header_fields[field_name] = cells[value_i]

        current_band = ""
        for row in table[header_idx + 1:]:
            cells = [_fix_concatenated_words(str(c).strip()) if c else "" for c in row]
            non_empty = [c for c in cells if c]
            if not non_empty:
                continue
            if len(non_empty) == 1 and cells[0]:
                # Category banner row (only column 0 filled)
                current_band = cells[0]
                continue
            tr = TestResult(category_label=current_band, category="")
            if "test_name" in col_map and col_map["test_name"] < len(cells):
                tr.test_name = cells[col_map["test_name"]]
            if "specification" in col_map and col_map["specification"] < len(cells):
                tr.specification = cells[col_map["specification"]]
            if "result" in col_map and col_map["result"] < len(cells):
                tr.result = cells[col_map["result"]]
            if "unit" in col_map and col_map["unit"] < len(cells):
                tr.unit = cells[col_map["unit"]]
            if "method" in col_map and col_map["method"] < len(cells):
                tr.method = cells[col_map["method"]]
            if "pass_fail" in col_map and col_map["pass_fail"] < len(cells):
                tr.pass_fail = _infer_pass_fail(cells[col_map["pass_fail"]])
            elif tr.result:
                tr.pass_fail = _infer_pass_fail(tr.result)
            if tr.test_name or tr.result:
                results.append(tr)

    return results, best_conf, header_fields


def map_from_text(text: str, extra_aliases: dict | None = None) -> tuple[COADocument, FieldConfidence]:
    """
    Extract COA fields from free text using regex patterns.
    Returns (COADocument, FieldConfidence).
    """
    doc = COADocument()
    conf: FieldConfidence = {}

    def extract(pattern: re.Pattern, attr: str, transform=None, base_conf: float = 0.75):
        val, c = _first_match(pattern, text)
        if val:
            if transform:
                val = transform(val)
            setattr(doc, attr, val)
            conf[attr] = c

    extract(_LOT, "lot_number")
    extract(_PRODUCT_NAME, "product_name")
    extract(_MANUFACTURER, "manufacturer_name")
    extract(_SUPPLIER_NAME, "supplier_name")
    extract(_CERT_NUMBER, "certificate_number")
    extract(_PO_NUMBER, "purchase_order_number")
    extract(_QUANTITY, "quantity_received")
    extract(_COUNTRY, "manufacturer_country")
    extract(_MFG_DATE, "manufacturing_date", _parse_date)
    extract(_EXP_DATE, "expiry_date", _parse_date)
    extract(_RETEST_DATE, "retest_date", _parse_date)

    # Apply custom aliases from user config
    if extra_aliases:
        for field_key, alias_list in extra_aliases.items():
            if getattr(doc, field_key, "") or not hasattr(doc, field_key):
                continue
            for alias in alias_list:
                pattern = re.compile(
                    rf'{re.escape(alias)}\s*[：:＃#\-]?\s*(.{{1,80}})',
                    re.IGNORECASE,
                )
                m = pattern.search(text)
                if m:
                    setattr(doc, field_key, m.group(1).strip())
                    conf[field_key] = 0.70
                    break

    return doc, conf


# ---------------------------------------------------------------------------
# Category keyword detection — used when the document has no dedicated
# "Botanical name"-style field to key off of (see apply_structured_extraction
# for that more reliable signal).
# ---------------------------------------------------------------------------
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Botanical": ["botanical", "plant", "herb", "leaf", "leaves", "root", "fruit",
                  "flower", "seed", "bark", "rhizome", "extract"],
    "Vitamins": ["vitamin", "tocopherol", "ascorbic", "retinol", "cholecalciferol",
                 "riboflavin", "niacin", "biotin", "folate", "pyridoxine",
                 "thiamine", "cobalamin"],
    "Amino Acids": ["amino acid", "lysine", "leucine", "glutamine", "taurine",
                     "arginine", "glycine", "alanine", "tryptophan", "methionine",
                     "proline", "threonine", "valine", "isoleucine",
                     "phenylalanine", "histidine", "cysteine", "tyrosine", "serine"],
    "Mineral": ["mineral", "calcium", "magnesium", "zinc", "iron", "selenium",
                "chromium", "potassium", "manganese", "copper", "citrate",
                "gluconate", "carbonate", "sulfate"],
}


def detect_product_category(full_text: str, product_name: str = "") -> str:
    """Scan document text for category-indicative keywords. Checked in
    Botanical -> Vitamins -> Amino Acids -> Mineral order; returns "" if
    nothing matches."""
    haystack = f"{product_name or ''} {full_text or ''}".lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if re.search(rf'\b{re.escape(kw)}\b', haystack):
                return category
    return ""


def apply_fallbacks(
    doc: COADocument,
    conf: FieldConfidence,
    full_text: str = "",
) -> tuple[COADocument, FieldConfidence]:
    """Post-processing fallbacks applied once after all extraction paths
    have run: Date of Analysis defaults to the manufacturing date when the
    supplier's document doesn't state it separately, and product_category
    gets a best-effort keyword-based guess when nothing set it already."""
    if not doc.date_of_analysis and doc.manufacturing_date:
        doc.date_of_analysis = doc.manufacturing_date
        conf["date_of_analysis"] = 0.5

    if not doc.product_category:
        category = detect_product_category(full_text, doc.product_name)
        if category:
            doc.product_category = category
            conf["product_category"] = 0.6
            if category == "Botanical":
                if not doc.supplier_batch_number:
                    doc.supplier_batch_number = doc.lot_number
                new_batch = generate_batch_number(doc.product_name, doc.manufacturing_date, "Botanical")
                if new_batch:
                    doc.lot_number = new_batch
                    conf["lot_number"] = 0.6

    return doc, conf


def apply_structured_extraction(
    doc: COADocument,
    conf: FieldConfidence,
    structured: dict,
) -> tuple[COADocument, FieldConfidence]:
    """
    Override header fields and test_results with a position-based structured
    extraction result (see pdf_parser._extract_structured_coa). This takes
    priority over the regex/pdfplumber path since it's anchored to the
    document's actual layout rather than free-text pattern matching.

    Auto-detects the Botanical product category when a `botanical_name` was
    found, and immediately regenerates the Batch No. for that case.
    """
    _DATE_FIELDS = {"manufacturing_date", "date_of_analysis", "retest_date", "expiry_date"}

    header_fields = structured.get("header_fields", {})
    for field_name, value in header_fields.items():
        if value:
            if field_name in _DATE_FIELDS:
                value = _parse_date(value)
            setattr(doc, field_name, value)
            conf[field_name] = 0.95

    if header_fields.get("lot_number"):
        doc.supplier_batch_number = header_fields["lot_number"]

    raw_results = structured.get("test_results", [])
    if raw_results:
        doc.test_results = [
            TestResult(
                test_name=r.get("test_name", ""),
                category_label=r.get("category_label", ""),
                category="",
                specification=r.get("specification", ""),
                result=r.get("result", ""),
                method=r.get("method", ""),
                pass_fail=_infer_pass_fail(r.get("result", "")),
            )
            for r in raw_results
        ]
        conf["test_results"] = 0.95

    if doc.botanical_name:
        doc.product_category = "Botanical"
        doc.lot_number = generate_batch_number(doc.product_name, doc.manufacturing_date, "Botanical")
        conf["product_category"] = 0.9
        conf["lot_number"] = 0.9

    return doc, conf


_DATE_FIELDS = {"manufacturing_date", "date_of_analysis", "retest_date", "expiry_date"}

# pdfplumber's per-cell text is immune to the PDF reading-order glitches that
# can corrupt the flattened-text regex path (see lot_number "Batch" row
# reordering), so always prefer it for these fields. For everything else,
# pdfplumber sometimes drops spaces between words in its cell text — so the
# table value is only used to fill a gap, not to override a regex value
# that's already there.
_FIELDS_PREFER_TABLE = {"lot_number", "quantity_received"}


def merge_documents(
    text_doc: COADocument,
    text_conf: FieldConfidence,
    table_results: list[TestResult],
    table_conf: float,
    table_header_fields: dict[str, str] | None = None,
) -> tuple[COADocument, FieldConfidence]:
    """
    Merge text-extracted header fields with table-extracted test results
    and (when present) a product-info grid found inside the same
    ruled-line table.
    """
    text_doc.test_results = table_results
    if table_results:
        text_conf["test_results"] = table_conf

    for field_name, value in (table_header_fields or {}).items():
        if not value:
            continue
        if field_name in _DATE_FIELDS:
            value = _parse_date(value)
        if field_name == "lot_number":
            text_doc.supplier_batch_number = value
        existing = getattr(text_doc, field_name, "")
        if existing and field_name not in _FIELDS_PREFER_TABLE:
            continue
        setattr(text_doc, field_name, value)
        text_conf[field_name] = 0.9

    return text_doc, text_conf
