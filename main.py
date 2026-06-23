"""
main.py — Entry point for COA Converter desktop application.
"""
import sys
import os

# PyInstaller frozen-binary path fix for Tesseract
if getattr(sys, "frozen", False):
    _base = sys._MEIPASS
    os.environ["TESSDATA_PREFIX"] = os.path.join(_base, "tessdata")
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = os.path.join(_base, "tesseract.exe")
    except ImportError:
        pass

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from views.main_window import MainWindow
from views.styles import QSS


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("COA Converter")
    app.setOrganizationName("COAConverter")
    app.setStyleSheet(QSS)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
