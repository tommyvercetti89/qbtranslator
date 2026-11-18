# -*- mode: python ; coding: utf-8 -*-
"""QBTranslator onedir package. Fast startup and low runtime memory."""

from __future__ import annotations

import sys

sys.path.insert(0, SPECPATH)

from spec_common import ASSETS, DATAS, EXCLUDES, ROOT, SRC, apply_filters

a = Analysis(
    [str(ROOT / "build_tools" / "entry.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=DATAS,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=2,
)

apply_filters(a)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="QBTranslator",
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
    icon=str(ASSETS / "QBTranslator.ico"),
    version=str(ROOT / "build_tools" / "version_info.txt"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="QBTranslator",
)
