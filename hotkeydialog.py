"""
hotkeydialog.py — Klavyeden kısayol yakalama penceresi.

Kullanıcı "Yakala" dediğinde bu pencere açılır; istediği kombinasyona
basar, "Kaydet" ile onaylar. Global kısayollar diyalog açıkken durdurulur
(yoksa mevcut kısayol tetiklenir ve tuş pencereye ulaşmaz).
"""

from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk

from win32util import get_modifier_flags, parse_hotkey

MODIFIER_KEYSYMS = {
    "Control_L",
    "Control_R",
    "Shift_L",
    "Shift_R",
    "Alt_L",
    "Alt_R",
    "Win_L",
    "Win_R",
    "Super_L",
    "Super_R",
    "Caps_Lock",
    "Num_Lock",
}

SPECIAL_KEY_TOKENS = {
    "space": "space",
    "Return": "enter",
    "KP_Enter": "enter",
    "Escape": "esc",
    "Tab": "tab",
    "BackSpace": "backspace",
    "Delete": "delete",
    "Insert": "insert",
    "Home": "home",
    "End": "end",
    "Prior": "pageup",
    "Next": "pagedown",
    "Left": "left",
    "Up": "up",
    "Right": "right",
    "Down": "down",
}

# Shift ile basılan rakamların keysym karşılıkları
SHIFTED_DIGITS = {
    "exclam": "1",
    "at": "2",
    "numbersign": "3",
    "dollar": "4",
    "percent": "5",
    "asciicircum": "6",
    "ampersand": "7",
    "asterisk": "8",
    "parenleft": "9",
    "parenright": "0",
}


def keysym_to_token(keysym: str) -> str | None:
    """Tk keysym'ini kısayol belirtecine çevirir (yoksa None)."""
    if not keysym:
        return None
    if keysym in SHIFTED_DIGITS:
        return SHIFTED_DIGITS[keysym]
    if len(keysym) == 1 and keysym.isascii():
        if keysym.isalpha():
            return keysym.lower()
        if keysym.isdigit():
            return keysym
    match = re.fullmatch(r"[fF]([1-9]|1[0-2])", keysym)
    if match:
        return "f" + match.group(1)
    return SPECIAL_KEY_TOKENS.get(keysym)


def compose_hotkey(
    keysym: str, ctrl: bool, alt: bool, shift: bool
) -> tuple[str | None, str]:
    """Tuş bilgilerinden 'ctrl+alt+t' biçiminde spec üretir: (spec, hata)."""
    token = keysym_to_token(keysym)
    if not token:
        return None, (
            "Bu tuş desteklenmiyor. Harf, rakam, F1–F12 veya Space/Tab/Enter gibi bir tuş deneyin."
        )
    modifiers: list[str] = []
    if ctrl:
        modifiers.append("ctrl")
    if alt:
        modifiers.append("alt")
    if shift:
        modifiers.append("shift")
    if not modifiers:
        return None, "En az bir değiştirici tuş gerekli (Ctrl, Alt veya Shift)."

    spec = "+".join(modifiers + [token])
    try:
        parse_hotkey(spec)
    except ValueError as error:
        return None, str(error)
    return spec, ""


class HotkeyCaptureDialog:
    """Modal kısayol yakalama penceresi. show() sonucu spec veya None döndürür."""

    def __init__(self, parent: tk.Misc, initial: str = "") -> None:
        self._result: str | None = None
        self._spec: str | None = None

        self.win = tk.Toplevel(parent)
        self.win.title("Kısayol Yakala")
        self.win.geometry("500x260")
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.grab_set()
        self.win.configure(bg="#f8fafc")
        self.win.protocol("WM_DELETE_WINDOW", self._cancel)
        self.win.bind("<KeyPress>", self._on_key)
        self.win.bind("<Escape>", lambda _e: self._cancel())

        tk.Label(
            self.win,
            text="İstediğiniz kısayol kombinasyonuna basın",
            bg="#f8fafc",
            fg="#0f172a",
            font=("Segoe UI Semibold", 13),
        ).pack(pady=(18, 4))
        tk.Label(
            self.win,
            text="Ctrl / Alt / Shift ile birlikte harf, rakam veya F1–F12 kullanın.",
            bg="#f8fafc",
            fg="#64748b",
            font=("Segoe UI", 9),
        ).pack()

        self.combo_var = tk.StringVar(value=initial or "…")
        tk.Label(
            self.win,
            textvariable=self.combo_var,
            bg="#ffffff",
            fg="#2563eb",
            font=("Consolas", 18, "bold"),
            relief="solid",
            borderwidth=1,
            padx=14,
            pady=10,
        ).pack(fill="x", padx=36, pady=16)

        self.status_var = tk.StringVar(value="")
        self.status_label = tk.Label(
            self.win,
            textvariable=self.status_var,
            bg="#f8fafc",
            fg="#b91c1c",
            font=("Segoe UI", 9),
            wraplength=440,
            justify="center",
        )
        self.status_label.pack(fill="x", padx=24)

        buttons = tk.Frame(self.win, bg="#f8fafc")
        buttons.pack(pady=14)

        ttk.Button(buttons, text="Temizle", command=self._clear).pack(side="left", padx=4)
        ttk.Button(buttons, text="İptal", command=self._cancel).pack(side="left", padx=4)
        self.save_button = ttk.Button(
            buttons, text="Kaydet", command=self._save, state="disabled"
        )
        self.save_button.pack(side="left", padx=4)

        tk.Label(
            self.win,
            text="Not: Win tuşu içeren kombinasyonları Ayarlar alanına elle yazabilirsiniz.",
            bg="#f8fafc",
            fg="#94a3b8",
            font=("Segoe UI", 8),
        ).pack(side="bottom", pady=(0, 10))

        self.win.update_idletasks()
        parent_x = parent.winfo_rootx() + max(0, (parent.winfo_width() - 500) // 2)
        parent_y = parent.winfo_rooty() + max(0, (parent.winfo_height() - 260) // 2)
        self.win.geometry(f"+{parent_x}+{parent_y}")
        self.win.after(80, self._focus)

        if initial:
            try:
                parse_hotkey(initial)
                self._spec = initial
                self.save_button.configure(state="normal")
            except ValueError:
                self._spec = None

    def _focus(self) -> None:
        try:
            self.win.focus_force()
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    def _on_key(self, event) -> str:
        if event.keysym in MODIFIER_KEYSYMS:
            self.status_var.set("Şimdi bir harf, rakam veya F tuşuna basın…")
            self.status_label.configure(fg="#64748b")
            return "break"

        ctrl, alt, shift = get_modifier_flags()
        spec, error = compose_hotkey(event.keysym, ctrl, alt, shift)
        if spec:
            self._spec = spec
            self.combo_var.set(spec)
            self.status_var.set("Uygun — Kaydet'e basın.")
            self.status_label.configure(fg="#15803d")
            self.save_button.configure(state="normal")
        else:
            self._spec = None
            self.combo_var.set("…")
            self.status_var.set(error)
            self.status_label.configure(fg="#b91c1c")
            self.save_button.configure(state="disabled")
        return "break"

    def _clear(self) -> None:
        self._spec = None
        self.combo_var.set("…")
        self.status_var.set("Yeni kombinasyon için tuşlara basın.")
        self.status_label.configure(fg="#64748b")
        self.save_button.configure(state="disabled")

    def _save(self) -> None:
        if self._spec:
            self._result = self._spec
            self.win.destroy()

    def _cancel(self) -> None:
        self._result = None
        self.win.destroy()

    def show(self) -> str | None:
        self.win.wait_window()
        return self._result
