"""
review_screen.py — Screen 3: Review & Edit extracted COA data
Left: scrollable header fields with confidence colouring
Right: test results QTableWidget with add/remove rows
"""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel,
    QLineEdit, QTextEdit, QComboBox, QPushButton, QScrollArea,
    QFormLayout, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from core.coa_model import (
    COADocument, TestResult, FIELD_LABELS,
    PassFail, Disposition, TestCategory,
)
from core.field_mapper import FieldConfidence

CONF_COLORS = {
    "ok":       "#FFFFFF",
    "low":      "#FFF8E1",
    "very_low": "#FFF3E0",
}


def _conf_color(conf: float) -> str:
    if conf >= 0.80:
        return CONF_COLORS["ok"]
    if conf >= 0.55:
        return CONF_COLORS["low"]
    return CONF_COLORS["very_low"]


class ReviewScreen(QWidget):
    generate_requested = pyqtSignal(object)  # COADocument

    def __init__(self, parent=None):
        super().__init__(parent)
        self._doc: COADocument | None = None
        self._conf: FieldConfidence = {}
        self._field_widgets: dict[str, QWidget] = {}
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 15, 20, 15)
        root.setSpacing(10)

        title = QLabel("Review & Edit COA Data")
        title.setObjectName("ScreenTitle")
        root.addWidget(title)

        legend = QLabel(
            "⬜ White = high confidence   🟡 Yellow = moderate (check)   🟠 Orange = low (review required)"
        )
        legend.setStyleSheet("font-size:11px; color:#666;")
        root.addWidget(legend)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left: header fields ──────────────────────────────────────────────
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 8, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        form_w = QWidget()
        self._form = QFormLayout(form_w)
        self._form.setSpacing(7)
        self._form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        scroll.setWidget(form_w)
        left_layout.addWidget(scroll)

        # Build form rows
        self._add_section("Product Identification")
        self._add_field("product_name", required=True)
        self._add_field("lot_number", required=True)
        self._add_field("internal_item_code")
        self._add_field("supplier_product_code")
        self._add_field("quantity_received")
        self._add_field("purchase_order_number")

        self._add_section("Manufacturer / Supplier")
        self._add_field("manufacturer_name", required=True)
        self._add_field("manufacturer_address", multi=True)
        self._add_field("manufacturer_country")
        self._add_field("supplier_name")

        self._add_section("Dates")
        self._add_field("date_of_analysis", required=True)
        self._add_field("date_received")
        self._add_field("manufacturing_date")
        self._add_field("expiry_date")
        self._add_field("retest_date")

        self._add_section("QC Release")
        self._add_disposition_row()
        self._add_field("qc_release_statement", multi=True)
        self._add_field("authorised_signatory_name")
        self._add_field("authorised_signatory_title")
        self._add_field("signature_date")

        splitter.addWidget(left)

        # ── Right: test results table ─────────────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)

        tr_label = QLabel("Test Results")
        tr_label.setObjectName("SectionLabel")
        right_layout.addWidget(tr_label)

        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(
            ["Test Name", "Category", "Specification", "Result", "Unit", "Method", "Pass/Fail"]
        )
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setAlternatingRowColors(True)
        self._table.setColumnWidth(0, 140)
        self._table.setColumnWidth(1, 110)
        self._table.setColumnWidth(2, 120)
        self._table.setColumnWidth(3, 90)
        self._table.setColumnWidth(4, 60)
        self._table.setColumnWidth(5, 110)
        right_layout.addWidget(self._table)

        # Table buttons
        tbl_btn_row = QHBoxLayout()
        add_row_btn = QPushButton("+ Add Row")
        add_row_btn.setObjectName("SecondaryBtn")
        add_row_btn.clicked.connect(self._add_table_row)
        del_row_btn = QPushButton("Remove Selected")
        del_row_btn.setObjectName("DangerBtn")
        del_row_btn.clicked.connect(self._remove_table_row)
        tbl_btn_row.addWidget(add_row_btn)
        tbl_btn_row.addWidget(del_row_btn)
        tbl_btn_row.addStretch()
        right_layout.addLayout(tbl_btn_row)

        splitter.addWidget(right)
        splitter.setSizes([380, 500])
        root.addWidget(splitter)

        # Bottom action bar
        bottom_row = QHBoxLayout()
        self._validate_btn = QPushButton("Validate")
        self._validate_btn.setObjectName("SecondaryBtn")
        self._validate_btn.clicked.connect(self._validate)
        self._generate_btn = QPushButton("Generate COA →")
        self._generate_btn.clicked.connect(self._emit_generate)
        bottom_row.addWidget(self._validate_btn)
        bottom_row.addStretch()
        bottom_row.addWidget(self._generate_btn)
        root.addLayout(bottom_row)

    def _add_section(self, title: str):
        lbl = QLabel(f"  {title}")
        lbl.setObjectName("SectionLabel")
        lbl.setMinimumHeight(26)
        self._form.addRow(lbl)

    def _add_field(self, field_key: str, required=False, multi=False):
        label_text = FIELD_LABELS.get(field_key, field_key.replace("_", " ").title())
        if required:
            label_text += " *"
        if multi:
            w = QTextEdit()
            w.setFixedHeight(55)
        else:
            w = QLineEdit()
        self._field_widgets[field_key] = w
        self._form.addRow(label_text, w)

    def _add_disposition_row(self):
        combo = QComboBox()
        for d in Disposition:
            combo.addItem(d.value)
        self._field_widgets["overall_disposition"] = combo
        self._form.addRow("Overall Disposition", combo)

    def _add_table_row(self, tr: TestResult | None = None):
        row = self._table.rowCount()
        self._table.insertRow(row)

        cat_combo = QComboBox()
        for c in TestCategory:
            cat_combo.addItem(c.value)

        pf_combo = QComboBox()
        for p in PassFail:
            pf_combo.addItem(p.value)

        cols = [
            QTableWidgetItem(tr.test_name if tr else ""),
            None,  # combo — set below
            QTableWidgetItem(tr.specification if tr else ""),
            QTableWidgetItem(tr.result if tr else ""),
            QTableWidgetItem(tr.unit if tr else ""),
            QTableWidgetItem(tr.method if tr else ""),
            None,  # combo — set below
        ]

        for col, item in enumerate(cols):
            if item is None:
                continue
            self._table.setItem(row, col, item)

        if tr:
            idx = cat_combo.findText(tr.category)
            if idx >= 0:
                cat_combo.setCurrentIndex(idx)
            idx2 = pf_combo.findText(tr.pass_fail)
            if idx2 >= 0:
                pf_combo.setCurrentIndex(idx2)

        self._table.setCellWidget(row, 1, cat_combo)
        self._table.setCellWidget(row, 6, pf_combo)
        self._table.setRowHeight(row, 30)

    def _remove_table_row(self):
        rows = self._table.selectionModel().selectedRows()
        for row in sorted(rows, reverse=True):
            self._table.removeRow(row.row())

    def _apply_confidence(self):
        for field_key, widget in self._field_widgets.items():
            conf = self._conf.get(field_key, 0.0)
            color = _conf_color(conf)
            if isinstance(widget, (QLineEdit, QTextEdit)):
                widget.setStyleSheet(
                    f"background-color: {color};"
                    + ("border: 1.5px solid #E65100;" if color == CONF_COLORS["very_low"] else "")
                )

    def load(self, doc: COADocument, conf: FieldConfidence):
        self._doc = doc
        self._conf = conf

        # Populate header fields
        for field_key, widget in self._field_widgets.items():
            val = getattr(doc, field_key, "")
            if isinstance(widget, QLineEdit):
                widget.setText(str(val))
            elif isinstance(widget, QTextEdit):
                widget.setPlainText(str(val))
            elif isinstance(widget, QComboBox):
                idx = widget.findText(str(val))
                if idx >= 0:
                    widget.setCurrentIndex(idx)

        self._apply_confidence()

        # Populate test results table
        self._table.setRowCount(0)
        for tr in doc.test_results:
            self._add_table_row(tr)

    def _collect_doc(self) -> COADocument:
        doc = self._doc or COADocument()

        for field_key, widget in self._field_widgets.items():
            if isinstance(widget, QLineEdit):
                setattr(doc, field_key, widget.text().strip())
            elif isinstance(widget, QTextEdit):
                setattr(doc, field_key, widget.toPlainText().strip())
            elif isinstance(widget, QComboBox):
                setattr(doc, field_key, widget.currentText())

        # Collect test results
        results: list[TestResult] = []
        for row in range(self._table.rowCount()):
            def cell(col) -> str:
                item = self._table.item(row, col)
                return item.text().strip() if item else ""
            def combo_val(col) -> str:
                w = self._table.cellWidget(row, col)
                return w.currentText() if w else ""

            tr = TestResult(
                test_name=cell(0),
                category=combo_val(1),
                specification=cell(2),
                result=cell(3),
                unit=cell(4),
                method=cell(5),
                pass_fail=combo_val(6),
            )
            results.append(tr)
        doc.test_results = results
        return doc

    def _validate(self):
        doc = self._collect_doc()
        missing = doc.validate()
        # Reset all required field backgrounds
        for field_key, widget in self._field_widgets.items():
            if isinstance(widget, QLineEdit):
                conf = self._conf.get(field_key, 0.0)
                widget.setStyleSheet(f"background-color: {_conf_color(conf)};")
        if missing:
            for f in missing:
                w = self._field_widgets.get(f)
                if w and isinstance(w, QLineEdit):
                    w.setStyleSheet("background-color:#FFEBEE; border:1.5px solid #C0392B;")
            labels = [FIELD_LABELS.get(f, f) for f in missing]
            QMessageBox.warning(self, "Validation",
                                f"The following required fields are missing:\n• " + "\n• ".join(labels))
        else:
            QMessageBox.information(self, "Validation", "✓ All required fields are present.")

    def _emit_generate(self):
        doc = self._collect_doc()
        self.generate_requested.emit(doc)
