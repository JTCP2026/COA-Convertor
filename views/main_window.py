"""
main_window.py — QMainWindow with sidebar navigation and QStackedWidget
"""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt
from core.config_manager import load_config
from core.coa_model import COADocument
from core.field_mapper import FieldConfidence
from views.setup_screen import SetupScreen
from views.upload_screen import UploadScreen
from views.review_screen import ReviewScreen
from views.export_screen import ExportScreen

SCREEN_SETUP = 0
SCREEN_UPLOAD = 1
SCREEN_REVIEW = 2
SCREEN_EXPORT = 3


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("COA Converter")
        self.setMinimumSize(1100, 720)
        self._nav_buttons: list[QPushButton] = []
        self._init_ui()
        self._check_first_run()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFrameShape(QFrame.Shape.StyledPanel)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        app_title = QLabel("COA Converter")
        app_title.setObjectName("SidebarTitle")
        sidebar_layout.addWidget(app_title)

        app_sub = QLabel("FDA-Compliant Document Tool")
        app_sub.setObjectName("SidebarSubtitle")
        sidebar_layout.addWidget(app_sub)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #1E4D8C;")
        sidebar_layout.addWidget(sep)

        nav_items = [
            ("⚙  Company Setup", SCREEN_SETUP),
            ("📂  Upload Document", SCREEN_UPLOAD),
            ("✏  Review & Edit", SCREEN_REVIEW),
            ("📄  Export COA", SCREEN_EXPORT),
        ]
        for label, idx in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("NavBtn")
            btn.setProperty("active", "false")
            btn.clicked.connect(lambda checked, i=idx: self._navigate(i))
            self._nav_buttons.append(btn)
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        version_lbl = QLabel("v1.0.0")
        version_lbl.setStyleSheet("color:#4A7090; font-size:10px; padding:10px 16px;")
        sidebar_layout.addWidget(version_lbl)

        root.addWidget(sidebar)

        # ── Content area ──────────────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.setObjectName("ContentArea")

        self._setup_screen = SetupScreen()
        self._upload_screen = UploadScreen()
        self._review_screen = ReviewScreen()
        self._export_screen = ExportScreen()

        self._stack.addWidget(self._setup_screen)
        self._stack.addWidget(self._upload_screen)
        self._stack.addWidget(self._review_screen)
        self._stack.addWidget(self._export_screen)

        root.addWidget(self._stack)

        # ── Wire signals ──────────────────────────────────────────────────────
        self._setup_screen.config_saved.connect(self._on_config_saved)
        self._upload_screen.extraction_done.connect(self._on_extraction_done)
        self._review_screen.generate_requested.connect(self._on_generate)
        self._export_screen.start_new.connect(self._on_start_new)

        self._navigate(SCREEN_SETUP)

    def _check_first_run(self):
        cfg = load_config()
        if not cfg.is_configured():
            # Lock upload/review/export until setup is done
            self._nav_buttons[SCREEN_UPLOAD].setEnabled(False)
            self._nav_buttons[SCREEN_REVIEW].setEnabled(False)
            self._nav_buttons[SCREEN_EXPORT].setEnabled(False)

    def _on_config_saved(self):
        self._nav_buttons[SCREEN_UPLOAD].setEnabled(True)
        cfg = load_config()
        self._upload_screen.set_aliases(cfg.custom_aliases)

    def _navigate(self, index: int):
        self._stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_buttons):
            btn.setProperty("active", "true" if i == index else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _on_extraction_done(self, doc: COADocument, conf: FieldConfidence):
        self._review_screen.load(doc, conf)
        self._nav_buttons[SCREEN_REVIEW].setEnabled(True)
        self._navigate(SCREEN_REVIEW)

    def _on_generate(self, doc: COADocument):
        self._export_screen.load(doc)
        self._nav_buttons[SCREEN_EXPORT].setEnabled(True)
        self._navigate(SCREEN_EXPORT)

    def _on_start_new(self):
        self._upload_screen.reset()
        self._nav_buttons[SCREEN_REVIEW].setEnabled(False)
        self._nav_buttons[SCREEN_EXPORT].setEnabled(False)
        self._navigate(SCREEN_UPLOAD)
