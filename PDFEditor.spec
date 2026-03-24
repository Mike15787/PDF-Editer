# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for PDF Editor.
Build: run build.bat (or `pyinstaller PDFEditor.spec` inside the venv).
"""

import sys
from PyInstaller.utils.hooks import collect_all

# Collect all PyMuPDF & PyQt6 data/binaries automatically
mupdf_datas, mupdf_bins, mupdf_hiddens = collect_all("fitz")
qt_datas,    qt_bins,    qt_hiddens    = collect_all("PyQt6")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=mupdf_bins + qt_bins,
    datas=mupdf_datas + qt_datas,
    hiddenimports=mupdf_hiddens + qt_hiddens + [
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.sip",
        "fitz",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,      # onedir mode (faster startup than onefile)
    name="PDFEditor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,              # no console window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="icon.ico",          # uncomment and set path if you have an icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PDFEditor",           # output folder: dist/PDFEditor/
)
