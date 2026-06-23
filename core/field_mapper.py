"""
field_mapper.py
Maps raw extracted text/tables to COADocument fields.
Returns (COADocument, FieldConfidence dict).
"""
from __future__ import annotations
import re
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
    r'|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s\-,\.]\d{1,2}[\s,\.]\d{4}'
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
    r'(?:quantity|qty\.?|amount|weight|volume|net[\s_-]*weight|gross[\s_-]*weight)[\s_-]*(?:received)?\s*[:#\-]?\s*(\d[\d,\.]*\s*(?:kg|g|mg|lb|lbs|l|ml|L|mL|units?|pcs?|bags?|drums?))',
    r'(?:数量|重量|净重|毛重|体积|容量)[\s_-]*(?:收货)?\s*[：:]\s*(\d[\d,\.]*\s*(?:千克|公斤|克|毫克|升|毫升|件|包|桶))',
])

_COUNTRY = _build([
    r'(?:country[\s_-]*of[\s_-]*(?:origin|manufacture|manufacturing)|origin)\s*[:#\-]?\s*([A-Za-z一-鿿]{2,50})',
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

# Table header keywords for column detection
_TABLE_HEADER_KEYWORDS = {
    "test_name": ["test", "parameter", "item", "检验项目", "项目", "检测项目", "测试项目", "指标"],
    "specification": ["specification", "spec", "standard", "requirement", "limit", "规格", "标准", "指标", "限度", "质量标准"],
    "result": ["result", "value", "found", "actual", "observed", "结果", "测定值", "实测值", "检测结果"],
    "method": ["method", "procedure", "standard", "方法", "检验方法", "检测方法", "依据"],
    "pass_fail": ["pass", "fail", "conform", "status", "判定", "结论", "合格"],
    "unit": ["unit", "units", "单位"],
    "category": ["category", "type", "类别", "类型"],
}


def _first_match(pattern: re.Pattern, text: str) -> tuple[str, float]:
    """Return (value, confidence) for first regex match."""
    m = pattern.search(text)
    if not m:
        return "", 0.0
    for g in m.groups():
        if g:
            return g.strip(), 0.75
    return "", 0.0


def _parse_date(raw: str) -> str:
    """Normalise any date string to YYYY-MM-DD. Returns raw on failure."""
    raw = raw.strip()
    try:
        dt = dateutil_parser.parse(raw, dayfirst=True)
        # Sanity check
        if 1990 <= dt.year <= 2050:
            return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    return raw


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


def map_from_tables(tables: list[list[list[str]]]) -> tuple[list[TestResult], float]:
    """Extract TestResult list from structured tables. Returns (results, confidence)."""
    results: list[TestResult] = []
    best_conf = 0.0

    for table in tables:
        if len(table) < 2:
            continue
        header_row = [str(c) for c in table[0]]
        col_map = _score_header_row(header_row)
        if "test_name" not in col_map and "result" not in col_map:
            continue

        conf = 0.95 if len(col_map) >= 3 else 0.70
        best_conf = max(best_conf, conf)

        for row in table[1:]:
            cells = [str(c).strip() if c else "" for c in row]
            if not any(cells):
                continue
            tr = TestResult()
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
            tr.category = _detect_category(tr.test_name)
            if tr.test_name or tr.result:
                results.append(tr)

    return results, best_conf


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


def merge_documents(
    text_doc: COADocument,
    text_conf: FieldConfidence,
    table_results: list[TestResult],
    table_conf: float,
) -> tuple[COADocument, FieldConfidence]:
    """
    Merge text-extracted header fields with table-extracted test results.
    Boosts confidence when both sources agree.
    """
    text_doc.test_results = table_results
    if table_results:
        text_conf["test_results"] = table_conf
    return text_doc, text_conf
