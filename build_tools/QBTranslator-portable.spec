# -*- mode: python ; coding: utf-8 -*-
"""QBTranslator — taşınabilir tek dosya (onefile) derleme tanımı.

Kurulum gerektirmeyen sürüm içindir. Sürüm bilgisi/metadata eklenmez;
yalnızca uygulama ikonu gömülür. Onedir kurulum sürümü hızlı başlangıç
için ayrıca üretilir.
"""

import os

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

EXCLUDES = [
    "unittest",
    "unittest.mock",
    "doctest",
    "pydoc",
    "pydoc_data",
    "test",
    "tests",
    "distutils",
    "setuptools",
    "pkg_resources",
    "wheel",
    "pip",
    "ensurepip",
    "venv",
    "lib2to3",
    "sqlite3",
    "_sqlite3",
    "xmlrpc",
    "http.server",
    "socketserver",
    "cgi",
    "cgitb",
    "multiprocessing",
    "asyncio",
    "concurrent",
    "bz2",
    "_bz2",
    "lzma",
    "_lzma",
    "turtle",
    "turtledemo",
    "idlelib",
    "numpy",
    "PIL",
    "pandas",
    "matplotlib",
    "scipy",
    "cv2",
    "PyQt5",
    "PyQt6",
    "PySide2",
    "PySide6",
    "wx",
    "IPython",
    "jupyter",
    "notebook",
    "pytest",
    "jedi",
    "parso",
]

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=2,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="QBTranslator-Portable",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, "assets", "QBTranslator.ico"),
)
