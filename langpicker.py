"""
langpicker.py — Aranabilir hedef dil seçici.

Türkçe ve İngilizce dil adlarıyla arama yapar; Türkçe karakterler
yazılmadan da (örn. "ingilizce", "turkce") eşleşir.
Balonun içinden açılır; seçim yapılana kadar balonun otomatik
kapanması askıya alınır (popup tarafında yönetilir).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from langs import filter_target_languages

BG = "#141a21"
BG_HEADER = "#1b232d"
BG_BUTTON = "#242e3a"
FG = "#e8eef6"
MUTED = "#93a1b1"
ACCENT = "#4da3ff"
BORDER = "#33404f"
ERR_RED = "#ff7b7b"

FONT_UI = ("Segoe UI", 9)
FONT_ENTRY = ("Segoe UI", 10)
FONT_LIST = ("Segoe UI", 10)


class LanguagePicker:
    def __init__(
        self,
        parent: tk.Misc,
        anchor: tk.Misc,
        current_code: str,
        on_select,
        on_close,
    ) -> None:
        self.parent = parent
        self.anchor = anchor
        self.on_select = on_select
        self.on_close = on_close
        self.closed = False
        self._results: list[tuple[str, str]] = []

        self.win = tk.Toplevel(parent)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg=BORDER)

        outer = tk.Frame(
            self.win, bg=BG, highlightbackground=BORDER, highlightthickness=1
        )
        outer.pack(fill="both", expand=True)

        pad = tk.Frame(outer, bg=BG, padx=10, pady=8)
        pad.pack(fill="both", expand=True)

        tk.Label(
            pad,
            text="Dil ara  (Türkçe veya English)",
            bg=BG,
            fg=MUTED,
            font=FONT_UI,
            anchor="w",
        ).pack(fill="x")

        self.var = tk.StringVar()
        self.entry = tk.Entry(
            pad,
            textvariable=self.var,
            bg=BG_BUTTON,
            fg=FG,
            insertbackground=FG,
            relief="flat",
            font=FONT_ENTRY,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
        )
        self.entry.pack(fill="x", pady=(5, 6), ipady=5)

        list_wrap = tk.Frame(pad, bg=BG)
        list_wrap.pack(fill="both", expand=True)

        self.listbox = tk.Listbox(
            list_wrap,
            bg=BG,
            fg=FG,
            font=FONT_LIST,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            activestyle="none",
            selectbackground=ACCENT,
            selectforeground="#06121f",
        )
        scrollbar = ttk.Scrollbar(
            list_wrap, orient="vertical", command=self.listbox.yview
        )
        self.listbox.configure(yscrollcommand=scrollbar.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.count_label = tk.Label(
            pad,
            text="",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 8),
            anchor="w",
        )
        self.count_label.pack(fill="x", pady=(6, 0))

        self._populate("", preselect_code=current_code)

        self.var.trace_add("write", lambda *_: self._on_type())
        self.entry.bind("<Return>", lambda _e: self._choose_first())
        self.entry.bind("<Escape>", lambda _e: self.close())
        self.entry.bind("<Down>", self._focus_list)
        self.listbox.bind("<Return>", lambda _e: self._choose_selected())
        self.listbox.bind("<Escape>", lambda _e: self.close())
        self.listbox.bind("<ButtonRelease-1>", self._choose_clicked)
        self.listbox.bind("<MouseWheel>", self._on_wheel)
        self.win.bind("<Escape>", lambda _e: self.close())

        self._position()
        self.win.deiconify()
        self.win.lift()
        try:
            self.entry.focus_force()
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    # Arama / liste
    # ------------------------------------------------------------------
    def _on_type(self) -> None:
        self._populate(self.var.get())

    def _populate(self, query: str, preselect_code: str | None = None) -> None:
        self.listbox.delete(0, "end")
        self._results = filter_target_languages(query)
        if self._results:
            for label, _code in self._results:
                self.listbox.insert("end", label)
            index = 0
            if preselect_code:
                for i, (_label, code) in enumerate(self._results):
                    if code == preselect_code:
                        index = i
                        break
            self.listbox.selection_set(index)
            self.listbox.see(index)
            self.count_label.configure(text=f"{len(self._results)} dil")
        else:
            self.listbox.insert("end", "  (eşleşme yok)")
            self.count_label.configure(text="Eşleşen dil bulunamadı")
        self.listbox.configure(fg=FG if self._results else MUTED)

    def _focus_list(self, _event=None):
        if not self._results:
            return "break"
        if self.listbox.curselection():
            index = int(self.listbox.curselection()[0])
        else:
            index = 0
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(index)
        self.listbox.activate(index)
        self.listbox.focus_set()
        return "break"

    def _on_wheel(self, event):
        self.listbox.yview_scroll(int(-event.delta / 120), "units")
        return "break"

    # ------------------------------------------------------------------
    # Seçim / kapanış
    # ------------------------------------------------------------------
    def _choose_first(self) -> None:
        if self._results:
            self._choose_index(0)

    def _choose_selected(self) -> None:
        selection = self.listbox.curselection()
        if selection:
            self._choose_index(int(selection[0]))

    def _choose_clicked(self, event) -> None:
        if not self._results:
            return
        index = self.listbox.nearest(event.y)
        bbox = self.listbox.bbox(index)
        if not bbox:
            return
        _x, y, _width, height = bbox
        if not (y <= event.y <= y + height):
            return
        self._choose_index(index)

    def _choose_index(self, index: int) -> None:
        if not (0 <= index < len(self._results)):
            return
        _label, code = self._results[index]
        self.close()
        self.on_select(code)

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        try:
            self.win.destroy()
        except tk.TclError:
            pass
        try:
            self.on_close()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Konum
    # ------------------------------------------------------------------
    def _position(self) -> None:
        try:
            self.win.update_idletasks()
            width = max(320, int(self.anchor.winfo_width()) + 120)
            height = 360
            pos_x = int(self.anchor.winfo_rootx())
            pos_y = int(self.anchor.winfo_rooty() + self.anchor.winfo_height() + 4)

            screen_w = self.win.winfo_screenwidth()
            screen_h = self.win.winfo_screenheight()

            if pos_x + width > screen_w - 10:
                pos_x = max(10, screen_w - width - 10)
            if pos_y + height > screen_h - 40:
                pos_y = max(10, int(self.anchor.winfo_rooty()) - height - 4)

            self.win.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
        except tk.TclError:
            self.win.geometry("340x360+200+200")
