# COA Converter — Setup & Build Guide

## 1. Prerequisites

- Python 3.11+
- (Optional for OCR on scanned PDFs) Tesseract OCR:
  - Windows: https://github.com/UB-Mannheim/tesseract/wiki
  - Install with English + Simplified Chinese language packs

## 2. Development Setup

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

## 3. Run (Development)

```bash
python main.py
```

## 4. Package as Standalone Executable (Windows)

```bash
# 1. Install PyInstaller
pip install pyinstaller

# 2. Edit coa_converter.spec — set TESSERACT_PATH to your Tesseract install folder
#    Default: C:\Program Files\Tesseract-OCR

# 3. Build
pyinstaller coa_converter.spec --clean --noconfirm

# 4. Output is in dist\COA_Converter\
#    Zip this folder and distribute to other PCs.
#    User just unzips and double-clicks COA_Converter.exe
```

## 4b. Build a Real Installer (Setup.exe)

After step 4 produces `dist\COA_Converter\`, wrap it into a proper Windows installer
(install wizard, desktop shortcut, Start menu entry, uninstaller) using Inno Setup:

```bash
# 1. Install Inno Setup (free): https://jrsoftware.org/isinfo.php

# 2. Open installer.iss in the Inno Setup Compiler (or right-click -> "Compile")
#    Or compile from the command line:
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

# 3. Output: Output\COA_Converter_Setup.exe
#    Distribute this single file — users double-click it to install,
#    no Python required on the target machine.
```

## 5. Data Storage

User settings (company info, logo, cert counter) are stored in:
- Windows: `%APPDATA%\COAConverter\config.json`
- Mac: `~/Library/Application Support/COAConverter/config.json`

These persist across application updates.

## 6. Adding Custom Keywords

In the Setup screen, add custom field aliases under "Custom Field Aliases":
```
内部批号 → lot_number
BBD → expiry_date
WH-LOT → lot_number
```
This teaches the extractor to recognise non-standard supplier terminology.
