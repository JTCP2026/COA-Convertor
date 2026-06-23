# coa_converter.spec — PyInstaller spec for COA Converter
# Usage: pyinstaller coa_converter.spec --clean --noconfirm
#
# Before building on Windows:
#   1. Install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki
#   2. Set TESSERACT_PATH below to your Tesseract installation folder
#   3. Run: pip install pyinstaller && pyinstaller coa_converter.spec --clean

import os
from PyInstaller.utils.hooks import collect_all

TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR"  # ← adjust if needed

datas_fitz, binaries_fitz, hiddenimports_fitz = collect_all("fitz")
datas_pdfplumber, binaries_pdfplumber, hiddenimports_pdfplumber = collect_all("pdfplumber")

extra_datas = [
    ("assets/", "assets/"),
    ("core/", "core/"),
    ("generators/", "generators/"),
    ("views/", "views/"),
    ("workers/", "workers/"),
]

# Bundle Tesseract binary + language data if path exists
if os.path.exists(TESSERACT_PATH):
    tesseract_exe = os.path.join(TESSERACT_PATH, "tesseract.exe")
    tessdata_dir = os.path.join(TESSERACT_PATH, "tessdata")
    if os.path.exists(tesseract_exe):
        extra_datas.append((tesseract_exe, "."))
    if os.path.exists(tessdata_dir):
        extra_datas.append((tessdata_dir, "tessdata"))

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=binaries_fitz + binaries_pdfplumber,
    datas=datas_fitz + datas_pdfplumber + extra_datas,
    hiddenimports=(
        hiddenimports_fitz
        + hiddenimports_pdfplumber
        + [
            "platformdirs",
            "dateutil",
            "dateutil.parser",
            "PIL",
            "PIL.Image",
            "docx",
            "docx.oxml",
            "reportlab",
            "reportlab.platypus",
            "reportlab.lib.pagesizes",
            "pytesseract",
        ]
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="COA_Converter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # No console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/app_icon.ico" if os.path.exists("assets/app_icon.ico") else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="COA_Converter",
)
