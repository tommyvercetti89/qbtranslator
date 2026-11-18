"""Shared PyInstaller settings for QBTranslator."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
ASSETS = SRC / "qbtranslator" / "assets"
LOCALES = SRC / "qbtranslator" / "locales"

EXCLUDES = [
    # Development and test tooling
    "tkinter",
    "_tkinter",
    "turtle",
    "turtledemo",
    "idlelib",
    "unittest",
    "doctest",
    "pydoc",
    "pydoc_data",
    "pdb",
    "bdb",
    "profile",
    "cProfile",
    "pstats",
    "timeit",
    "trace",
    "distutils",
    "setuptools",
    "pkg_resources",
    "wheel",
    "pip",
    "ensurepip",
    "venv",
    "virtualenv",
    "lib2to3",
    "test",
    "tests",
    "pytest",
    "jedi",
    "parso",
    # Unused standard library modules
    "sqlite3",
    "_sqlite3",
    "dbm",
    "decimal",
    "_decimal",
    "xmlrpc",
    "http.server",
    "socketserver",
    "cgi",
    "cgitb",
    "wsgiref",
    "multiprocessing",
    "asyncio",
    "concurrent",
    "bz2",
    "_bz2",
    "lzma",
    "_lzma",
    # Unused third-party packages
    "numpy",
    "PIL",
    "pandas",
    "matplotlib",
    "scipy",
    "cv2",
    "IPython",
    "jupyter",
    "notebook",
    "PyQt5",
    "PyQt6",
    "PySide2",
    "wx",
    "win32",
    "win32api",
    "win32evtlog",
    "win32com",
    "pythonwin",
    "pywintypes",
    "pywin32_system32",
    # Unused Qt modules
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
    "PySide6.QtQuickControls2",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebChannel",
    "PySide6.QtWebSockets",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtNetwork",
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    "PySide6.QtSql",
    "PySide6.QtTest",
    "PySide6.QtXml",
    "PySide6.QtConcurrent",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtPrintSupport",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtGraphs",
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.QtPositioning",
    "PySide6.QtLocation",
    "PySide6.QtSerialPort",
    "PySide6.QtSensors",
    "PySide6.QtHelp",
    "PySide6.QtDesigner",
    "PySide6.QtUiTools",
    "PySide6.QtStateMachine",
    "PySide6.QtScxml",
    "PySide6.QtRemoteObjects",
    "PySide6.QtTextToSpeech",
    "PySide6.QtHttpServer",
    "PySide6.QtWebView",
]

DATAS = [
    (str(LOCALES), "qbtranslator/locales"),
    (str(ASSETS), "qbtranslator/assets"),
]

_UNUSED_QT_DLLS = {
    "opengl32sw.dll",
    "d3dcompiler_47.dll",
    "libegl.dll",
    "libglesv2.dll",
    "qt6svg.dll",
    "qt6network.dll",
    "qt6qml.dll",
    "qt6qmlmodels.dll",
    "qt6qmlworkerscript.dll",
    "qt6quick.dll",
    "qt6quickcontrols2.dll",
    "qt6quicktemplates2.dll",
    "qt6quickwidgets.dll",
    "qt6quickdialogs2.dll",
    "qt6opengl.dll",
    "qt6openglwidgets.dll",
    "qt6multimedia.dll",
    "qt6multimediawidgets.dll",
    "qt6sql.dll",
    "qt6test.dll",
    "qt6xml.dll",
    "qt6concurrent.dll",
    "qt6pdf.dll",
    "qt6pdfwidgets.dll",
    "qt6charts.dll",
    "qt6datavisualization.dll",
    "qt6graphs.dll",
    "qt6bluetooth.dll",
    "qt6nfc.dll",
    "qt6positioning.dll",
    "qt6location.dll",
    "qt6serialport.dll",
    "qt6sensors.dll",
    "qt6help.dll",
    "qt6designer.dll",
    "qt6uitools.dll",
    "qt6statemachine.dll",
    "qt6scxml.dll",
    "qt6remoteobjects.dll",
    "qt6texttospeech.dll",
    "qt6qmlmeta.dll",
    "qt6virtualkeyboard.dll",
    "qt6httpserver.dll",
    "qt6webview.dll",
    "qt6webenginecore.dll",
    "qt6webenginewidgets.dll",
    "qt6webenginequick.dll",
    "qt6webchannel.dll",
    "qt6websockets.dll",
    "pyside6qml.abi3.dll",
}


def _normalized(value: str) -> str:
    return value.replace("\\", "/").lower()


def keep_binary(entry) -> bool:
    destination = _normalized(entry[0])
    name = os.path.basename(destination)
    if name in _UNUSED_QT_DLLS:
        return False
    if "/imageformats/" in destination:
        return name in {"qico.dll", "qpng.dll"}
    if "/platforms/" in destination:
        return name in {"qwindows.dll", "qoffscreen.dll"}
    if any(
        marker in destination
        for marker in (
            "/iconengines/",
            "/styles/",
            "/translations/",
            "/tls/",
            "/networkinformation/",
            "/platformthemes/",
            "/printsupport/",
            "/multimedia/",
            "/egldeviceintegrations/",
            "/generic/",
            "/platforminputcontexts/",
        )
    ):
        return False
    if "/pywin32_system32/" in destination or "/win32/" in destination:
        return False
    return True


def keep_data(entry) -> bool:
    destination = _normalized(entry[0])
    return "/translations/" not in destination


def apply_filters(analysis) -> None:
    analysis.binaries = [entry for entry in analysis.binaries if keep_binary(entry)]
    analysis.datas = [entry for entry in analysis.datas if keep_data(entry)]
