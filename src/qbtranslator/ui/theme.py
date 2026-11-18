"""PySide6 prototipi için tema ve QSS."""

from __future__ import annotations

from qbtranslator.core.paths import ASSETS_DIR

BG = "#0b0f14"
SIDEBAR = "#0e141b"
PANEL = "#121922"
PANEL_ALT = "#17202b"
INPUT = "#0f151d"
BORDER = "#243040"
BORDER_SOFT = "#1b2634"
TEXT = "#e8eef6"
MUTED = "#8fa0b5"
ACCENT = "#4da3ff"
ACCENT_DARK = "#2b7fe0"
GREEN = "#5ecb8a"
RED = "#ff7b7b"
YELLOW = "#f6c177"

QSS = f"""
* {{
    font-family: "Segoe UI";
    font-size: 10.5pt;
    font-weight: 500;
    color: {TEXT};
}}
QMainWindow, QWidget#Root {{
    background: {BG};
}}
QWidget#Sidebar {{
    background: {SIDEBAR};
    border-right: 1px solid {BORDER_SOFT};
}}
QFrame#Card {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 14px;
}}
QFrame#PopupPanel {{
    background: #141a21;
    border: 1px solid #33404f;
    border-radius: 16px;
}}
QLabel#Brand {{
    font-size: 20pt;
    font-weight: 600;
    color: #f5f9ff;
}}
QLabel#BrandSub {{
    color: {MUTED};
    font-size: 9pt;
}}
QLabel#PageTitle {{
    font-size: 17pt;
    font-weight: 600;
    color: #f5f9ff;
}}
QLabel#SectionTitle {{
    font-size: 11pt;
    font-weight: 600;
    color: #dfe9f5;
}}
QLabel#Muted {{
    color: {MUTED};
}}
QLabel#Tiny {{
    color: #6f8197;
    font-size: 8pt;
}}
QLabel#Status {{
    color: {MUTED};
    font-size: 9pt;
}}
QLabel#Error {{
    color: {RED};
}}
QLabel#Success {{
    color: {GREEN};
}}
QLabel#Chip {{
    background: #16202c;
    border: 1px solid #27384b;
    border-radius: 8px;
    padding: 5px 9px;
    color: #9ec8ff;
    font-size: 8pt;
}}
QPushButton {{
    background: #1b2532;
    border: 1px solid #2b394a;
    border-radius: 9px;
    padding: 8px 14px;
    color: #dbe6f3;
}}
QPushButton:hover {{
    background: #243244;
    border-color: #3c5067;
}}
QPushButton:pressed {{
    background: #17202b;
}}
QPushButton:disabled {{
    color: #5e6d7e;
    background: #151d26;
    border-color: #202b38;
}}
QPushButton#Accent {{
    background: {ACCENT_DARK};
    border: 1px solid {ACCENT_DARK};
    color: #ffffff;
    font-weight: 600;
}}
QPushButton#Accent:hover {{
    background: #3b90f0;
    border-color: #3b90f0;
}}
QPushButton#Accent:disabled {{
    background: #151d26;
    border-color: #202b38;
    color: #5e6d7e;
}}
QPushButton#Ghost {{
    background: transparent;
    border: none;
    color: {MUTED};
    padding: 6px 8px;
}}
QPushButton#Ghost:hover {{
    color: #ffffff;
    background: #1a2532;
}}
QPushButton#Nav {{
    background: transparent;
    border: none;
    border-radius: 9px;
    padding: 10px 14px;
    text-align: left;
    color: {MUTED};
}}
QPushButton#Nav:hover {{
    background: #141d27;
    color: #dce8f5;
}}
QPushButton#Nav:checked {{
    background: #192739;
    color: #ffffff;
}}
QPushButton#Danger {{
    color: #ffb4b4;
    background: #2a171b;
    border-color: #4a252c;
}}
QPushButton#Danger:hover {{
    background: #3a1c22;
}}
QTextEdit, QTextBrowser, QLineEdit, QComboBox {{
    background: {INPUT};
    border: 1px solid #263346;
    border-radius: 9px;
    padding: 8px;
    selection-background-color: #2b7fe0;
    selection-color: #ffffff;
}}
QTextEdit:focus, QTextBrowser:focus, QLineEdit:focus, QComboBox:focus {{
    border-color: #3b7fbf;
}}
QTextBrowser {{
    border: none;
    background: transparent;
    padding: 2px;
}}
QComboBox {{
    padding: 7px 10px;
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background: #141d27;
    border: 1px solid #2b394a;
    border-radius: 8px;
    selection-background-color: #1f3a5c;
    outline: 0;
}}
QCheckBox {{
    spacing: 9px;
    color: #c9d6e5;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid #33455a;
    background: #101821;
}}
QCheckBox::indicator:checked {{
    background: {ACCENT_DARK};
    border-color: {ACCENT_DARK};
    image: url("{((ASSETS_DIR / 'check.png').as_posix())}");
}}
QListWidget {{
    background: transparent;
    border: none;
    outline: 0;
}}
QListWidget::item {{
    padding: 10px;
    border-radius: 8px;
    color: #c9d6e5;
}}
QListWidget::item:hover {{
    background: #16212d;
}}
QListWidget::item:selected {{
    background: #1a2e44;
    color: #ffffff;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #35465a;
    min-height: 24px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: #46607c;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QToolTip {{
    background: #1a2430;
    color: #e8eef6;
    border: 1px solid #33455a;
    padding: 6px;
}}
QFrame#Separator {{
    background: #243040;
    max-height: 1px;
    border: none;
}}
QLabel#PopupTitle {{
    color: #93a1b1;
    font-size: 9pt;
    font-weight: 600;
}}
QLabel#PopupSource {{
    color: #93a1b1;
    font-size: 9pt;
}}
QLabel#PopupResult {{
    color: #e8eef6;
    font-size: 12pt;
}}
QLabel#PopupStatus {{
    color: #93a1b1;
    font-size: 8pt;
}}
"""
