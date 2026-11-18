"""
mainwindow.py — Uygulamanın ana penceresi ve olay yönetimi.

Sekmeler: Çeviri | Geçmiş | Kayıtlı Kelimeler | Ayarlar | Hakkında
"""

from __future__ import annotations

import csv
import os
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import autostart
from appinfo import APP_NAME, APP_TITLE, APP_VERSION
from hotkeydialog import HotkeyCaptureDialog
from langs import (
    SOURCE_LABELS,
    TARGET_LABELS,
    code_to_label,
    label_to_code,
    lang_name,
)
from ocr import (
    ScreenRegionSelector,
    clear_last_capture,
    cleanup_temp_captures,
    last_capture_path,
    recognize_region,
)
from popup import TranslationPopup
from storage import DATA_DIR, DEFAULT_CONFIG, Store
from toggle import ToggleRow
from tray import TrayIcon
from translator import (
    ENGINE_LABELS,
    ENGINE_OPTIONS,
    translate,
)
from tts import SpeechEngine
from win32util import (
    ClipboardWatcher,
    GlobalHotkey,
    capture_selected_text,
    parse_hotkey,
    set_clipboard_text,
)

ENGINE_LABEL_TO_CODE = {label: code for label, code in ENGINE_OPTIONS}


def _shorten(text: str, limit: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


class ScrollFrame(ttk.Frame):
    """Dikey kaydırılabilir çerçeve (Ayarlar sekmesi için)."""

    def __init__(self, parent) -> None:
        super().__init__(parent)
        canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.inner = ttk.Frame(canvas, padding=16)

        window = canvas.create_window((0, 0), window=self.inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.inner.bind(
            "<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.bind(
            "<Configure>", lambda event: canvas.itemconfigure(window, width=event.width)
        )

        def _on_wheel(event):
            widget = self.winfo_containing(event.x_root, event.y_root)
            while widget is not None:
                if widget is canvas:
                    canvas.yview_scroll(int(-event.delta / 120), "units")
                    return
                widget = widget.master

        self.bind_all("<MouseWheel>", _on_wheel)


class StudyDialog:
    """Kayıtlı kelimelerle basit kart çalışma modu."""

    def __init__(self, app, words: list[dict]) -> None:
        self.app = app
        self.words = words
        self.index = 0
        self.revealed = False

        self.win = tk.Toplevel(app.root)
        self.win.title("Kelime Kartları")
        self.win.geometry("560x380")
        self.win.transient(app.root)
        self.win.configure(bg="#f8fafc")
        self.win.bind("<Escape>", lambda _e: self.win.destroy())
        self.win.bind("<space>", lambda _e: self._reveal())
        self.win.bind("<Right>", lambda _e: self._next())
        self.win.bind("<Left>", lambda _e: self._previous())

        self.counter = tk.Label(
            self.win, text="", bg="#f8fafc", fg="#64748b", font=("Segoe UI", 10)
        )
        self.counter.pack(pady=(18, 6))

        self.word_label = tk.Label(
            self.win,
            text="",
            bg="#f8fafc",
            fg="#0f172a",
            font=("Segoe UI Semibold", 26),
            wraplength=500,
            justify="center",
        )
        self.word_label.pack(padx=24, pady=(10, 6), fill="x")

        self.translation_label = tk.Label(
            self.win,
            text="",
            bg="#f8fafc",
            fg="#2563eb",
            font=("Segoe UI", 16),
            wraplength=500,
            justify="center",
        )
        self.translation_label.pack(padx=24, pady=8, fill="x")

        self.hint = tk.Label(
            self.win,
            text="Boşluk: cevabı göster   •   ← →: gezin",
            bg="#f8fafc",
            fg="#94a3b8",
            font=("Segoe UI", 9),
        )
        self.hint.pack(pady=(4, 10))

        buttons = tk.Frame(self.win, bg="#f8fafc")
        buttons.pack(pady=8)
        ttk.Button(buttons, text="← Önceki", command=self._previous).pack(side="left", padx=4)
        ttk.Button(buttons, text="Cevabı Göster", command=self._reveal).pack(side="left", padx=4)
        ttk.Button(buttons, text="Sonraki →", command=self._next).pack(side="left", padx=4)
        ttk.Button(buttons, text="Oku", command=self._speak).pack(side="left", padx=4)
        ttk.Button(buttons, text="Kapat", command=self.win.destroy).pack(side="left", padx=4)

        self._refresh()

    def _current(self) -> dict | None:
        if not self.words:
            return None
        return self.words[self.index]

    def _refresh(self) -> None:
        record = self._current()
        if not record:
            self.word_label.configure(text="Kayıtlı kelime yok")
            self.translation_label.configure(text="")
            self.counter.configure(text="")
            return
        self.counter.configure(
            text=f"{self.index + 1} / {len(self.words)}   •   {record.get('source_lang', '')} → {record.get('target_lang', '')}"
        )
        self.word_label.configure(text=record.get("word", ""))
        self.translation_label.configure(
            text=record.get("translation", "") if self.revealed else "• • • • • •"
        )
        self.hint.configure(
            text=(
                "Boşluk: cevabı göster   •   ← →: gezin"
                if not self.revealed
                else "← →: gezin   •   Boşluk: kapat/aç"
            )
        )

    def _reveal(self) -> None:
        self.revealed = not self.revealed
        self._refresh()

    def _next(self) -> None:
        if not self.words:
            return
        self.index = (self.index + 1) % len(self.words)
        self.revealed = False
        self._refresh()

    def _previous(self) -> None:
        if not self.words:
            return
        self.index = (self.index - 1) % len(self.words)
        self.revealed = False
        self._refresh()

    def _speak(self) -> None:
        record = self._current()
        if not record:
            return
        if self.app.is_speaking():
            self.app.stop_speaking()
        else:
            self.app.speak(record.get("translation", ""))


class TranslatorApp:
    def __init__(self, start_minimized: bool = False) -> None:
        self.store = Store()
        self.config = self.store.config
        self.start_minimized = start_minimized

        # Önceki oturumdan kalan OCR ekran görüntülerini temizle.
        clear_last_capture()
        cleanup_temp_captures()

        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.minsize(900, 640)
        self.root.option_add("*Font", ("Segoe UI", 10))
        try:
            self.root.tk.call("tk", "scaling", self.root.winfo_fpixels("1i") / 72.0)
        except tk.TclError:
            pass
        self._setup_styles()

        self.events: queue.Queue = queue.Queue()
        self.hotkey = GlobalHotkey()
        self.ocr_hotkey_listener = GlobalHotkey()
        self.clipboard = ClipboardWatcher(self._on_clipboard_text)
        self.tts = SpeechEngine()
        self.popup: TranslationPopup | None = None

        self._capturing = False
        self._suppress_clipboard_until = 0.0
        self._last_clipboard_text = ""
        self._manual_busy = False
        self._popup_seq = 0
        self._ocr_active = False
        self._ocr_selector = None
        self._history_map: dict[str, dict] = {}
        self._words_map: dict[str, dict] = {}
        self.tray: TrayIcon | None = None
        self._force_quit = False
        self._tray_hint_shown = False

        self._build_ui()
        self._load_settings_vars()
        self._reload_history()
        self._reload_words()
        self._apply_settings(initial=True)

        self.root.after(90, self._pump_events)
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)

        if self.start_minimized:
            if self.tray and self.tray.available:
                self.root.withdraw()
            else:
                self.root.iconify()

    # ==================================================================
    # Genel arayüz
    # ==================================================================
    def _setup_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        style.configure("Treeview", rowheight=26)
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 10))
        style.configure("TNotebook.Tab", padding=(16, 8))
        style.configure("TButton", padding=(10, 5))

    def _build_ui(self) -> None:
        self._build_header()
        self._build_status_bar()

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(10, 6))

        self._build_translate_tab()
        self._build_history_tab()
        self._build_words_tab()
        self._build_settings_tab()
        self._build_about_tab()

        geom = self.config.get("window_geometry")
        if geom and self._valid_geometry(geom):
            try:
                self.root.geometry(geom)
                return
            except tk.TclError:
                pass
        self.root.update_idletasks()
        width, height = 980, 700
        pos_x = (self.root.winfo_screenwidth() - width) // 2
        pos_y = (self.root.winfo_screenheight() - height) // 2
        self.root.geometry(f"{width}x{height}+{pos_x}+{pos_y}")

    @staticmethod
    def _valid_geometry(geometry: str) -> bool:
        try:
            size = geometry.split("+")[0].split("-")[0]
            width, height = (int(part) for part in size.split("x"))
            return width >= 700 and height >= 500
        except (ValueError, AttributeError):
            return False

    def _build_header(self) -> None:
        header = tk.Frame(self.root, bg="#0f172a")
        header.pack(fill="x")
        inner = tk.Frame(header, bg="#0f172a", padx=18, pady=12)
        inner.pack(fill="x")

        tk.Label(
            inner,
            text="QBTranslator",
            bg="#0f172a",
            fg="#ffffff",
            font=("Segoe UI Semibold", 17),
        ).pack(side="left")
        tk.Label(
            inner,
            text="  masaüstü çevirmen",
            bg="#0f172a",
            fg="#8ea4c1",
            font=("Segoe UI", 10),
        ).pack(side="left", pady=(7, 0))

        right = tk.Frame(inner, bg="#0f172a")
        right.pack(side="right")

        self.hotkey_chip = tk.Label(
            right,
            text="Kısayol: …",
            bg="#1e293b",
            fg="#93c5fd",
            font=("Segoe UI", 9),
            padx=10,
            pady=4,
        )
        self.hotkey_chip.pack(side="left", padx=(0, 8))

        self.monitor_chip = tk.Label(
            right,
            text="Pano izleme: kapalı",
            bg="#1e293b",
            fg="#93c5fd",
            font=("Segoe UI", 9),
            padx=10,
            pady=4,
        )
        self.monitor_chip.pack(side="left", padx=(0, 8))

        self.ocr_chip = tk.Label(
            right,
            text="OCR: kapalı",
            bg="#1e293b",
            fg="#93c5fd",
            font=("Segoe UI", 9),
            padx=10,
            pady=4,
        )
        self.ocr_chip.pack(side="left")

    def _build_status_bar(self) -> None:
        bar = tk.Frame(self.root, bg="#e2e8f0")
        bar.pack(fill="x", side="bottom")
        self.status_engine_label = tk.Label(
            bar,
            text="Hazır",
            bg="#e2e8f0",
            fg="#334155",
            font=("Segoe UI", 9),
            anchor="w",
        )
        self.status_engine_label.pack(side="left", padx=12, pady=5)
        self.status_hotkey_label = tk.Label(
            bar,
            text="",
            bg="#e2e8f0",
            fg="#334155",
            font=("Segoe UI", 9),
            anchor="e",
        )
        self.status_hotkey_label.pack(side="right", padx=12, pady=5)

    # ==================================================================
    # Sekme: Çeviri
    # ==================================================================
    def _build_translate_tab(self) -> None:
        page = ttk.Frame(self.notebook, padding=14)
        self.notebook.add(page, text="Çeviri")

        top = ttk.Frame(page)
        top.pack(fill="x")
        ttk.Label(top, text="Kaynak").pack(side="left")
        self.src_combo = ttk.Combobox(
            top, values=SOURCE_LABELS, state="readonly", width=27
        )
        self.src_combo.pack(side="left", padx=(6, 6))
        ttk.Button(top, text="⇄", width=3, command=self._swap_languages).pack(side="left")
        ttk.Label(top, text="Hedef").pack(side="left", padx=(12, 0))
        self.tgt_combo = ttk.Combobox(
            top, values=TARGET_LABELS, state="readonly", width=27
        )
        self.tgt_combo.pack(side="left", padx=(6, 0))
        self.tgt_combo.bind("<<ComboboxSelected>>", self._on_target_language_selected)

        ttk.Label(page, text="Çevrilecek metin").pack(anchor="w", pady=(12, 4))
        input_wrap = ttk.Frame(page)
        input_wrap.pack(fill="x")
        self.input_text = tk.Text(
            input_wrap,
            height=6,
            wrap="word",
            font=("Segoe UI", 11),
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=6,
            undo=True,
        )
        input_scroll = ttk.Scrollbar(input_wrap, orient="vertical", command=self.input_text.yview)
        self.input_text.configure(yscrollcommand=input_scroll.set)
        self.input_text.pack(side="left", fill="x", expand=True)
        input_scroll.pack(side="right", fill="y")
        self.input_text.bind("<Control-Return>", lambda _e: (self._manual_translate(), "break")[1])

        actions = ttk.Frame(page)
        actions.pack(fill="x", pady=(10, 4))

        self.btn_translate = tk.Button(
            actions,
            text="Çevir  (Ctrl+Enter)",
            command=self._manual_translate,
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            relief="flat",
            font=("Segoe UI Semibold", 10),
            padx=16,
            pady=6,
            cursor="hand2",
        )
        self.btn_translate.pack(side="left")
        ttk.Button(actions, text="Yapıştır", command=self._manual_paste).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(actions, text="Temizle", command=self._manual_clear).pack(
            side="left", padx=(8, 0)
        )

        result_header = ttk.Frame(page)
        result_header.pack(fill="x", pady=(12, 4))
        ttk.Label(result_header, text="Çeviri").pack(side="left")
        ttk.Button(result_header, text="Kelime Kaydet", command=self._save_manual_word).pack(
            side="right"
        )
        ttk.Button(result_header, text="Oku", command=self._speak_manual).pack(
            side="right", padx=(0, 6)
        )
        ttk.Button(result_header, text="Kopyala", command=self._copy_manual).pack(
            side="right", padx=(0, 6)
        )

        output_wrap = ttk.Frame(page)
        output_wrap.pack(fill="both", expand=True)
        self.output_text = tk.Text(
            output_wrap,
            height=9,
            wrap="word",
            font=("Segoe UI", 12),
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=6,
            state="disabled",
            cursor="arrow",
        )
        output_scroll = ttk.Scrollbar(
            output_wrap, orient="vertical", command=self.output_text.yview
        )
        self.output_text.configure(yscrollcommand=output_scroll.set)
        self.output_text.pack(side="left", fill="both", expand=True)
        output_scroll.pack(side="right", fill="y")

        self.manual_status = ttk.Label(page, text="", foreground="#64748b")
        self.manual_status.pack(anchor="w", pady=(6, 0))

        self.src_combo.set(code_to_label(self.config.get("source_lang", "auto")))
        self.tgt_combo.set(
            code_to_label(self.config.get("target_lang", "tr"), include_auto=False)
        )

    def _on_target_language_selected(self, _event=None) -> None:
        """Ana sekmede hedef dil değişince ayarı ve balonu da güncelle."""
        code = label_to_code(self.tgt_combo.get(), "tr")
        if code:
            self.set_target_language(code)

    def set_target_language(self, code: str) -> None:
        """Hedef dili her yerde günceller: ayar, ana sekme, ayarlar, balon, durum çubuğu."""
        if not code or code == "auto":
            return
        if self.config.get("target_lang") != code:
            self.config["target_lang"] = code
            self.store.save_config()
        label = code_to_label(code, include_auto=False)
        try:
            self.tgt_combo.set(label)
        except tk.TclError:
            pass
        if hasattr(self, "var_target"):
            self.var_target.set(label)
        if self.popup and self.popup.alive:
            self.popup.set_target_display(code)
        self._refresh_status_bar()

    def _swap_languages(self) -> None:
        source = label_to_code(self.src_combo.get(), "auto")
        target = label_to_code(self.tgt_combo.get(), "tr")
        if source == "auto":
            source = target
            target = "tr" if target != "tr" else "en"
        else:
            source, target = target, source
        self.src_combo.set(code_to_label(source))
        self.tgt_combo.set(code_to_label(target, include_auto=False))
        # Ana sekmedeki takas da global hedefi güncellesin (balon/ayarlar senkronu).
        if target:
            self.set_target_language(target)

    def _manual_paste(self) -> None:
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            text = ""
        if text:
            self.input_text.delete("1.0", "end")
            self.input_text.insert("1.0", text)

    def _manual_clear(self) -> None:
        self.input_text.delete("1.0", "end")
        self._set_manual_output("", error=False)
        self.manual_status.configure(text="")

    def _manual_translate(self) -> None:
        text = self.input_text.get("1.0", "end").strip()
        if not text:
            self.manual_status.configure(text="Çevrilecek metin boş.", foreground="#b91c1c")
            return
        if self._manual_busy:
            return
        source = label_to_code(self.src_combo.get(), "auto")
        target = label_to_code(self.tgt_combo.get(), "tr")
        if not target:
            self.manual_status.configure(text="Hedef dil seçin.", foreground="#b91c1c")
            return

        self._manual_busy = True
        self.btn_translate.configure(state="disabled", text="Çevriliyor…")
        self.manual_status.configure(text="Çevriliyor…", foreground="#64748b")
        self._translate_async(text, source, target, ("manual", text, source, target))

    def _set_manual_output(self, text: str, error: bool = False) -> None:
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", text)
        self.output_text.tag_configure("error", foreground="#b91c1c")
        if error:
            self.output_text.tag_add("error", "1.0", "end")
        self.output_text.configure(state="disabled")

    def _current_manual_text(self) -> str:
        return self.output_text.get("1.0", "end").strip()

    def _copy_manual(self) -> None:
        self.copy_to_clipboard(self._current_manual_text())
        self.manual_status.configure(text="Panoya kopyalandı.", foreground="#15803d")

    def _speak_manual(self) -> None:
        text = self._current_manual_text()
        if not text:
            return
        if self.is_speaking():
            self.stop_speaking()
            self.manual_status.configure(
                text="Sesli okuma durduruldu.", foreground="#64748b"
            )
        else:
            self.speak(text)
            self.manual_status.configure(
                text="Sesli okuma başladı… (durdurmak için tekrar Oku)", foreground="#64748b"
            )

    def _save_manual_word(self) -> None:
        text = self.input_text.get("1.0", "end").strip()
        translation = self._current_manual_text()
        if not text or not translation:
            self.manual_status.configure(
                text="Önce bir çeviri yapın.", foreground="#b91c1c"
            )
            return
        self.save_word(
            text,
            translation,
            label_to_code(self.src_combo.get(), "auto"),
            label_to_code(self.tgt_combo.get(), "tr"),
        )
        self.manual_status.configure(text="Kelime kaydedildi ✓", foreground="#15803d")

    # ==================================================================
    # Sekme: Geçmiş
    # ==================================================================
    def _build_history_tab(self) -> None:
        page = ttk.Frame(self.notebook, padding=14)
        self.notebook.add(page, text="Geçmiş")

        toolbar = ttk.Frame(page)
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Label(toolbar, text="Ara").pack(side="left")
        self.history_search_var = tk.StringVar()
        history_search = ttk.Entry(toolbar, textvariable=self.history_search_var, width=32)
        history_search.pack(side="left", padx=(6, 8))
        history_search.bind("<KeyRelease>", lambda _e: self._reload_history())
        ttk.Button(toolbar, text="Yenile", command=self._reload_history).pack(side="left")
        ttk.Button(
            toolbar, text="Seçileni Kopyala", command=self._copy_selected_history
        ).pack(side="right")
        ttk.Button(
            toolbar, text="Kelime Olarak Kaydet", command=self._save_selected_history_word
        ).pack(side="right", padx=(0, 6))
        ttk.Button(
            toolbar, text="Seçileni Sil", command=self._delete_selected_history
        ).pack(side="right", padx=(0, 6))
        ttk.Button(toolbar, text="Tümünü Temizle", command=self._clear_history).pack(
            side="right", padx=(0, 6)
        )

        columns = ("date", "source", "translation", "langs", "engine")
        self.history_tree = ttk.Treeview(page, columns=columns, show="headings")
        self.history_tree.heading("date", text="Tarih")
        self.history_tree.heading("source", text="Kaynak Metin")
        self.history_tree.heading("translation", text="Çeviri")
        self.history_tree.heading("langs", text="Diller")
        self.history_tree.heading("engine", text="Motor")
        self.history_tree.column("date", width=120, anchor="w")
        self.history_tree.column("source", width=300, anchor="w")
        self.history_tree.column("translation", width=300, anchor="w")
        self.history_tree.column("langs", width=90, anchor="center")
        self.history_tree.column("engine", width=120, anchor="w")
        self.history_tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(page, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        self.history_tree.bind("<Double-1>", lambda _e: self._open_selected_history_detail())

    def _reload_history(self) -> None:
        tree = self.history_tree
        tree.delete(*tree.get_children())
        query = self.history_search_var.get().strip().casefold()
        self._history_map = {}
        for record in self.store.history:
            if query:
                haystack = (
                    f"{record.get('source_text', '')} {record.get('translation', '')}".casefold()
                )
                if query not in haystack:
                    continue
            self._history_map[record["id"]] = record
            tree.insert(
                "",
                "end",
                iid=record["id"],
                values=(
                    record.get("ts", ""),
                    _shorten(record.get("source_text", ""), 90),
                    _shorten(record.get("translation", ""), 90),
                    f"{record.get('source_lang', '')}→{record.get('target_lang', '')}",
                    ENGINE_LABELS.get(record.get("engine", ""), record.get("engine", "")),
                ),
            )

    def _selected_history(self) -> dict | None:
        selection = self.history_tree.selection()
        if not selection:
            return None
        return self._history_map.get(selection[0])

    def _copy_selected_history(self) -> None:
        record = self._selected_history()
        if record:
            self.copy_to_clipboard(record.get("translation", ""))
            self._notify("Çeviri panoya kopyalandı ✓")

    def _save_selected_history_word(self) -> None:
        record = self._selected_history()
        if not record:
            messagebox.showinfo(APP_TITLE, "Önce listeden bir kayıt seçin.")
            return
        self.save_word(
            record.get("source_text", ""),
            record.get("translation", ""),
            record.get("source_lang", ""),
            record.get("target_lang", ""),
        )
        self._notify("Kelime kaydedildi ✓")

    def _delete_selected_history(self) -> None:
        record = self._selected_history()
        if not record:
            return
        if messagebox.askyesno(APP_TITLE, "Seçili kayıt silinsin mi?"):
            self.store.delete_history(record["id"])
            self._reload_history()

    def _clear_history(self) -> None:
        if not self.store.history:
            return
        if messagebox.askyesno(APP_TITLE, "Tüm çeviri geçmişi silinsin mi?"):
            self.store.clear_history()
            self._reload_history()

    def _open_selected_history_detail(self) -> None:
        record = self._selected_history()
        if not record:
            return
        self._open_detail(
            record.get("source_text", ""),
            record.get("translation", ""),
            f"{lang_name(record.get('source_lang', ''))} → {lang_name(record.get('target_lang', ''))}  •  {ENGINE_LABELS.get(record.get('engine', ''), '')}  •  {record.get('ts', '')}",
        )

    # ==================================================================
    # Sekme: Kayıtlı Kelimeler
    # ==================================================================
    def _build_words_tab(self) -> None:
        page = ttk.Frame(self.notebook, padding=14)
        self.notebook.add(page, text="Kayıtlı Kelimeler")

        toolbar = ttk.Frame(page)
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Label(toolbar, text="Ara").pack(side="left")
        self.words_search_var = tk.StringVar()
        words_search = ttk.Entry(toolbar, textvariable=self.words_search_var, width=32)
        words_search.pack(side="left", padx=(6, 8))
        words_search.bind("<KeyRelease>", lambda _e: self._reload_words())
        ttk.Button(toolbar, text="Yenile", command=self._reload_words).pack(side="left")
        ttk.Button(toolbar, text="Kart Modu", command=self._open_study_mode).pack(side="right")
        ttk.Button(toolbar, text="CSV Dışa Aktar", command=self._export_words_csv).pack(
            side="right", padx=(0, 6)
        )
        ttk.Button(toolbar, text="Seçileni Sil", command=self._delete_selected_word).pack(
            side="right", padx=(0, 6)
        )
        ttk.Button(toolbar, text="Tümünü Temizle", command=self._clear_words).pack(
            side="right", padx=(0, 6)
        )

        columns = ("word", "translation", "langs", "created")
        self.words_tree = ttk.Treeview(page, columns=columns, show="headings")
        self.words_tree.heading("word", text="Kelime")
        self.words_tree.heading("translation", text="Çeviri")
        self.words_tree.heading("langs", text="Diller")
        self.words_tree.heading("created", text="Tarih")
        self.words_tree.column("word", width=280, anchor="w")
        self.words_tree.column("translation", width=360, anchor="w")
        self.words_tree.column("langs", width=90, anchor="center")
        self.words_tree.column("created", width=130, anchor="w")
        self.words_tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(page, orient="vertical", command=self.words_tree.yview)
        self.words_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    def _reload_words(self) -> None:
        tree = self.words_tree
        tree.delete(*tree.get_children())
        query = self.words_search_var.get().strip().casefold()
        self._words_map = {}
        for record in self.store.words:
            if query:
                haystack = f"{record.get('word', '')} {record.get('translation', '')}".casefold()
                if query not in haystack:
                    continue
            self._words_map[record["id"]] = record
            tree.insert(
                "",
                "end",
                iid=record["id"],
                values=(
                    record.get("word", ""),
                    record.get("translation", ""),
                    f"{record.get('source_lang', '')}→{record.get('target_lang', '')}",
                    record.get("created", ""),
                ),
            )

    def _selected_word(self) -> dict | None:
        selection = self.words_tree.selection()
        if not selection:
            return None
        return self._words_map.get(selection[0])

    def _delete_selected_word(self) -> None:
        record = self._selected_word()
        if record and messagebox.askyesno(APP_TITLE, "Seçili kelime silinsin mi?"):
            self.store.delete_word(record["id"])
            self._reload_words()

    def _clear_words(self) -> None:
        if not self.store.words:
            return
        if messagebox.askyesno(APP_TITLE, "Tüm kayıtlı kelimeler silinsin mi?"):
            self.store.clear_words()
            self._reload_words()

    def _export_words_csv(self) -> None:
        if not self.store.words:
            messagebox.showinfo(APP_TITLE, "Dışa aktarılacak kelime yok.")
            return
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Kelimeleri dışa aktar",
            defaultextension=".csv",
            filetypes=[("CSV dosyası", "*.csv")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Kelime", "Çeviri", "Kaynak Dil", "Hedef Dil", "Tarih"])
                for record in self.store.words:
                    writer.writerow(
                        [
                            record.get("word", ""),
                            record.get("translation", ""),
                            record.get("source_lang", ""),
                            record.get("target_lang", ""),
                            record.get("created", ""),
                        ]
                    )
            messagebox.showinfo(APP_TITLE, f"Kelimeler kaydedildi:\n{path}")
        except OSError as error:
            messagebox.showerror(APP_TITLE, f"Dosya yazılamadı: {error}")

    def _open_study_mode(self) -> None:
        if not self.store.words:
            messagebox.showinfo(APP_TITLE, "Önce kelime kaydedin.")
            return
        StudyDialog(self, list(self.store.words))

    # ==================================================================
    # Sekme: Ayarlar
    # ==================================================================
    def _build_settings_tab(self) -> None:
        scroll = ScrollFrame(self.notebook)
        self.notebook.add(scroll, text="Ayarlar")
        page = scroll.inner
        card_bg = self._card_bg()

        # --- Büyük arka plan bilgisi ---------------------------------
        banner = tk.Frame(
            page, bg="#fff7ed", highlightbackground="#f59e0b", highlightthickness=1
        )
        banner.pack(fill="x", pady=(0, 14))
        tk.Label(
            banner,
            text="ARKA PLANDA ÇALIŞMA — X UYGULAMAYI KAPATMAZ",
            bg="#fff7ed",
            fg="#9a3412",
            font=("Segoe UI Semibold", 12),
            anchor="w",
            justify="left",
            wraplength=900,
        ).pack(fill="x", padx=14, pady=(12, 4))
        tk.Label(
            banner,
            text=(
                "X düğmesine bastığınızda uygulama SİSTEM TEPSİSİNE KÜÇÜLÜR; "
                "kısayollar dinlenmeye devam eder ve anında yanıt verir.\n"
                "Tamamen kapatmak için sistem tepsisindeki QBTranslator simgesine sağ tıklayıp "
                "'Çıkış'ı seçin veya aşağıdaki 'UYGULAMADAN TAMAMEN ÇIKIŞ' düğmesini kullanın."
            ),
            bg="#fff7ed",
            fg="#7c2d12",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            justify="left",
            wraplength=900,
        ).pack(fill="x", padx=14)
        banner_buttons = tk.Frame(banner, bg="#fff7ed")
        banner_buttons.pack(fill="x", padx=14, pady=(10, 12))
        tk.Button(
            banner_buttons,
            text="ARKA PLANA KÜÇÜLT",
            command=self._hide_to_tray,
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            relief="flat",
            font=("Segoe UI Semibold", 10),
            padx=12,
            pady=5,
            cursor="hand2",
        ).pack(side="left")
        tk.Button(
            banner_buttons,
            text="UYGULAMADAN TAMAMEN ÇIKIŞ",
            command=self._confirm_quit,
            bg="#dc2626",
            fg="white",
            activebackground="#b91c1c",
            activeforeground="white",
            relief="flat",
            font=("Segoe UI Semibold", 10),
            padx=12,
            pady=5,
            cursor="hand2",
        ).pack(side="left", padx=(10, 0))
        tk.Label(
            banner,
            text="Arka planda çalışırken RAM kullanımı düşüktür; kısayollar anında yanıt verir.",
            bg="#fff7ed",
            fg="#92400e",
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=14, pady=(0, 10))

        # --- Kısayol -------------------------------------------------
        hotkey_frame = ttk.LabelFrame(page, text="Genel", padding=12)
        hotkey_frame.pack(fill="x", pady=(0, 12))

        row = ttk.Frame(hotkey_frame)
        row.pack(fill="x")
        ttk.Label(row, text="Global kısayol:").pack(side="left")
        self.var_hotkey = tk.StringVar()
        ttk.Entry(row, textvariable=self.var_hotkey, width=22).pack(side="left", padx=8)
        ttk.Button(
            row,
            text="Yakala…",
            command=lambda: self._capture_hotkey(self.var_hotkey, "Çeviri kısayolu"),
        ).pack(side="left", padx=(0, 8))
        ttk.Label(
            row,
            text="Örn: ctrl+alt+t   (seçili metni çevirir)",
            foreground="#64748b",
        ).pack(side="left")

        self.var_autostart = tk.IntVar()
        ToggleRow(
            hotkey_frame,
            text="Windows açılışında otomatik başlat (arka planda, kısayolları dinler)",
            variable=self.var_autostart,
            bg=card_bg,
        ).pack(fill="x", pady=(12, 2))

        self.var_monitor = tk.IntVar()
        ToggleRow(
            hotkey_frame,
            text="Panoyu izle — kopyalanan metni otomatik çevir",
            variable=self.var_monitor,
            bg=card_bg,
        ).pack(fill="x", pady=(4, 2))

        self.var_restore = tk.IntVar()
        ToggleRow(
            hotkey_frame,
            text="Kısayol kullanınca eski pano içeriğini geri yükle",
            variable=self.var_restore,
            bg=card_bg,
        ).pack(fill="x", pady=(4, 2))

        # --- OCR -----------------------------------------------------
        ocr_frame = ttk.LabelFrame(page, text="OCR — Ekrandan Çeviri", padding=12)
        ocr_frame.pack(fill="x", pady=(0, 12))

        self.var_ocr_enabled = tk.IntVar()
        ToggleRow(
            ocr_frame,
            text="OCR modunu etkinleştir (ekran bölgesi seçerek çevir)",
            variable=self.var_ocr_enabled,
            bg=card_bg,
        ).pack(fill="x")

        ocr_row = ttk.Frame(ocr_frame)
        ocr_row.pack(fill="x", pady=(10, 0))
        ttk.Label(ocr_row, text="OCR kısayolu:").pack(side="left")
        self.var_ocr_hotkey = tk.StringVar()
        ttk.Entry(ocr_row, textvariable=self.var_ocr_hotkey, width=22).pack(
            side="left", padx=8
        )
        ttk.Button(
            ocr_row,
            text="Yakala…",
            command=lambda: self._capture_hotkey(self.var_ocr_hotkey, "OCR kısayolu"),
        ).pack(side="left", padx=(0, 8))
        ttk.Label(
            ocr_row,
            text="Örn: ctrl+alt+o",
            foreground="#64748b",
        ).pack(side="left")

        ttk.Label(
            ocr_frame,
            text=(
                "Ekranda seçtiğiniz alanın dışı kararır; bölge Windows OCR ile okunur ve\n"
                "aynı çeviri balonunda gösterilir. Windows OCR dil paketlerinin kurulu olması\n"
                "gerekir; kuruluysa Tesseract yedek olarak kullanılır."
            ),
            foreground="#64748b",
        ).pack(anchor="w", pady=(8, 0))

        # --- Çeviri --------------------------------------------------
        translate_frame = ttk.LabelFrame(page, text="Çeviri", padding=12)
        translate_frame.pack(fill="x", pady=(0, 12))

        target_row = ttk.Frame(translate_frame)
        target_row.pack(fill="x")
        ttk.Label(target_row, text="Varsayılan hedef dil:").pack(side="left")
        self.var_target = tk.StringVar()
        ttk.Combobox(
            target_row, textvariable=self.var_target, values=TARGET_LABELS,
            state="readonly", width=30,
        ).pack(side="left", padx=8)

        engine_row = ttk.Frame(translate_frame)
        engine_row.pack(fill="x", pady=(10, 0))
        ttk.Label(engine_row, text="Birincil motor:").pack(side="left")
        self.var_engine = tk.StringVar()
        self.engine_combo = ttk.Combobox(
            engine_row,
            textvariable=self.var_engine,
            values=[label for label, _code in ENGINE_OPTIONS],
            state="readonly",
            width=46,
        )
        self.engine_combo.pack(side="left", padx=8)
        self.engine_combo.bind("<<ComboboxSelected>>", self._on_engine_changed)

        self.var_backup = tk.IntVar()
        ToggleRow(
            translate_frame,
            text="Birincil motor başarısız olursa yedek motorları dene (MyMemory → Lingva → LibreTranslate)",
            variable=self.var_backup,
            bg=card_bg,
        ).pack(fill="x", pady=(10, 2))

        # --- Motor panelleri ----------------------------------------
        engine_frame = ttk.LabelFrame(page, text="Motor Ayarları", padding=12)
        engine_frame.pack(fill="x", pady=(0, 12))
        self.engine_panels: dict[str, ttk.Frame] = {}
        panel_container = ttk.Frame(engine_frame)
        panel_container.pack(fill="x")
        panel_container.columnconfigure(0, weight=1)

        def make_panel(key: str) -> ttk.Frame:
            panel = ttk.Frame(panel_container)
            panel.grid(row=0, column=0, sticky="ew")
            panel.grid_remove()
            self.engine_panels[key] = panel
            return panel

        google_panel = make_panel("google")
        ttk.Label(
            google_panel,
            text="Google Translate, ücretsiz genel uç noktayı kullanır. API anahtarı gerekmez.\n"
            "Yoğun kullanımda Google kısa süreli sınırlama uygulayabilir.",
            foreground="#475569",
        ).pack(anchor="w")

        mymemory_panel = make_panel("mymemory")
        ttk.Label(
            mymemory_panel,
            text="MyMemory ücretsiz API'dir; istek başına yaklaşık 500 karakter sınırı vardır.\n"
            "Kaynak dil 'Otomatik' seçiliyse önce Google ile dil algılanır.",
            foreground="#475569",
        ).pack(anchor="w")

        libretranslate_panel = make_panel("libretranslate")
        ttk.Label(libretranslate_panel, text="Uç nokta:").grid(row=0, column=0, sticky="w")
        self.var_libre_endpoint = tk.StringVar()
        ttk.Entry(libretranslate_panel, textvariable=self.var_libre_endpoint, width=52).grid(
            row=0, column=1, sticky="w", padx=8, pady=2
        )
        ttk.Label(libretranslate_panel, text="API anahtarı (isteğe bağlı):").grid(
            row=1, column=0, sticky="w"
        )
        self.var_libre_key = tk.StringVar()
        ttk.Entry(
            libretranslate_panel, textvariable=self.var_libre_key, width=52, show="•"
        ).grid(row=1, column=1, sticky="w", padx=8, pady=2)
        ttk.Label(
            libretranslate_panel,
            text="Genel libretranslate.com sunucusu çoğu zaman API anahtarı ister;\n"
            "kendi sunucunuzu veya anahtar destekleyen bir uç noktayı yazabilirsiniz.",
            foreground="#64748b",
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))

        lingva_panel = make_panel("lingva")
        ttk.Label(lingva_panel, text="Uç nokta:").grid(row=0, column=0, sticky="w")
        self.var_lingva_endpoint = tk.StringVar()
        ttk.Entry(lingva_panel, textvariable=self.var_lingva_endpoint, width=52).grid(
            row=0, column=1, sticky="w", padx=8, pady=2
        )
        ttk.Label(
            lingva_panel,
            text="Genel örnek: https://lingva.ml — kendi Lingva sunucunuzu da yazabilirsiniz.",
            foreground="#64748b",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        llm_panel = make_panel("llm")
        ttk.Label(llm_panel, text="Uç nokta:").grid(row=0, column=0, sticky="w")
        self.var_llm_endpoint = tk.StringVar()
        ttk.Entry(llm_panel, textvariable=self.var_llm_endpoint, width=52).grid(
            row=0, column=1, sticky="w", padx=8, pady=2
        )
        ttk.Label(llm_panel, text="Model:").grid(row=1, column=0, sticky="w")
        self.var_llm_model = tk.StringVar()
        ttk.Entry(llm_panel, textvariable=self.var_llm_model, width=52).grid(
            row=1, column=1, sticky="w", padx=8, pady=2
        )
        ttk.Label(llm_panel, text="API anahtarı (isteğe bağlı):").grid(
            row=2, column=0, sticky="w"
        )
        self.var_llm_key = tk.StringVar()
        ttk.Entry(llm_panel, textvariable=self.var_llm_key, width=52, show="•").grid(
            row=2, column=1, sticky="w", padx=8, pady=2
        )
        ttk.Label(
            llm_panel,
            text="Ollama: http://localhost:11434/v1   •   LM Studio: http://localhost:1234/v1\n"
            "OpenAI: https://api.openai.com/v1   •   Model örn: llama3.2 / gpt-4o-mini",
            foreground="#64748b",
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))

        # --- Görünüm / ses ------------------------------------------
        misc_frame = ttk.LabelFrame(page, text="Pencere ve Ses", padding=12)
        misc_frame.pack(fill="x", pady=(0, 12))

        misc_row = ttk.Frame(misc_frame)
        misc_row.pack(fill="x")
        ttk.Label(misc_row, text="Çeviri balonu otomatik kapansın (saniye, 0 = kapatma):").pack(
            side="left"
        )
        self.var_autohide = tk.IntVar()
        ttk.Spinbox(misc_row, from_=0, to=120, width=5, textvariable=self.var_autohide).pack(
            side="left", padx=8
        )
        ttk.Label(misc_row, text="Ses hızı (-10 … 10):").pack(side="left", padx=(16, 0))
        self.var_tts_rate = tk.IntVar()
        ttk.Spinbox(misc_row, from_=-10, to=10, width=5, textvariable=self.var_tts_rate).pack(
            side="left", padx=8
        )
        ttk.Label(misc_row, text="Geçmiş limiti:").pack(side="left", padx=(16, 0))
        self.var_history_limit = tk.IntVar()
        ttk.Spinbox(
            misc_row, from_=50, to=5000, increment=50, width=7, textvariable=self.var_history_limit
        ).pack(side="left", padx=8)

        # --- Kaydet ---------------------------------------------------
        save_row = ttk.Frame(page)
        save_row.pack(fill="x", pady=(4, 16))
        tk.Button(
            save_row,
            text="Ayarları Kaydet ve Uygula",
            command=self._save_settings,
            bg="#16a34a",
            fg="#ffffff",
            activebackground="#15803d",
            activeforeground="#ffffff",
            relief="flat",
            font=("Segoe UI Semibold", 10),
            padx=18,
            pady=7,
            cursor="hand2",
        ).pack(side="left")
        ttk.Button(save_row, text="Varsayılanlara Dön", command=self._reset_settings).pack(
            side="left", padx=(10, 0)
        )
        self.settings_status = ttk.Label(save_row, text="", foreground="#15803d")
        self.settings_status.pack(side="left", padx=12)

    def _on_engine_changed(self, _event=None) -> None:
        code = ENGINE_LABEL_TO_CODE.get(self.var_engine.get(), "google")
        for key, panel in self.engine_panels.items():
            if key == code:
                panel.grid()
            else:
                panel.grid_remove()

    def _load_settings_vars(self) -> None:
        cfg = self.config
        self.var_hotkey.set(cfg.get("hotkey", "ctrl+alt+t"))
        self.var_autostart.set(1 if cfg.get("autostart", True) else 0)
        self.var_ocr_enabled.set(1 if cfg.get("ocr_enabled") else 0)
        self.var_ocr_hotkey.set(cfg.get("ocr_hotkey", "ctrl+alt+o"))
        self.var_target.set(code_to_label(cfg.get("target_lang", "tr"), include_auto=False))
        engine_code = cfg.get("engine", "google")
        engine_label = next(
            (label for label, code in ENGINE_OPTIONS if code == engine_code),
            ENGINE_OPTIONS[0][0],
        )
        self.var_engine.set(engine_label)
        self.var_backup.set(1 if cfg.get("backup_engines") else 0)
        self.var_monitor.set(1 if cfg.get("clipboard_monitor") else 0)
        self.var_restore.set(1 if cfg.get("restore_clipboard", True) else 0)
        self.var_autohide.set(int(cfg.get("popup_autohide_seconds", 8) or 0))
        self.var_tts_rate.set(int(cfg.get("tts_rate", 0) or 0))
        self.var_history_limit.set(int(cfg.get("history_limit", 500) or 500))
        self.var_libre_endpoint.set(cfg.get("libretranslate_endpoint", ""))
        self.var_libre_key.set(cfg.get("libretranslate_api_key", ""))
        self.var_lingva_endpoint.set(cfg.get("lingva_endpoint", ""))
        self.var_llm_endpoint.set(cfg.get("llm_endpoint", ""))
        self.var_llm_model.set(cfg.get("llm_model", ""))
        self.var_llm_key.set(cfg.get("llm_api_key", ""))
        self._on_engine_changed()

    def _read_int(self, variable, fallback: int) -> int:
        try:
            return int(variable.get())
        except (tk.TclError, ValueError):
            return fallback

    def _save_settings(self) -> None:
        hotkey_spec = (self.var_hotkey.get() or "").strip().lower()
        try:
            parse_hotkey(hotkey_spec)
        except ValueError as exc:
            messagebox.showerror(APP_TITLE, f"Geçersiz kısayol:\n{exc}")
            return

        ocr_enabled = bool(self.var_ocr_enabled.get())
        ocr_hotkey_spec = (self.var_ocr_hotkey.get() or "").strip().lower()
        if ocr_enabled:
            try:
                parse_hotkey(ocr_hotkey_spec)
            except ValueError as exc:
                messagebox.showerror(APP_TITLE, f"Geçersiz OCR kısayolu:\n{exc}")
                return
            if ocr_hotkey_spec == hotkey_spec:
                messagebox.showerror(
                    APP_TITLE,
                    "OCR kısayolu, seçili metin çeviri kısayoluyla aynı olamaz.\n"
                    "Lütfen farklı bir kombinasyon seçin.",
                )
                return

        target = label_to_code(self.var_target.get(), "tr")
        engine = ENGINE_LABEL_TO_CODE.get(self.var_engine.get(), "google")

        self.config.update(
            {
                "hotkey": hotkey_spec,
                "ocr_hotkey": ocr_hotkey_spec or "ctrl+alt+o",
                "ocr_enabled": ocr_enabled,
                "autostart": bool(self.var_autostart.get()),
                "target_lang": target,
                "engine": engine,
                "backup_engines": bool(self.var_backup.get()),
                "clipboard_monitor": bool(self.var_monitor.get()),
                "restore_clipboard": bool(self.var_restore.get()),
                "popup_autohide_seconds": max(0, self._read_int(self.var_autohide, 8)),
                "tts_rate": max(-10, min(10, self._read_int(self.var_tts_rate, 0))),
                "history_limit": max(50, self._read_int(self.var_history_limit, 500)),
                "libretranslate_endpoint": self.var_libre_endpoint.get().strip(),
                "libretranslate_api_key": self.var_libre_key.get().strip(),
                "lingva_endpoint": self.var_lingva_endpoint.get().strip(),
                "llm_endpoint": self.var_llm_endpoint.get().strip(),
                "llm_model": self.var_llm_model.get().strip(),
                "llm_api_key": self.var_llm_key.get().strip(),
            }
        )
        self.store.save_config()
        self.tgt_combo.set(code_to_label(target, include_auto=False))
        if self.popup and self.popup.alive:
            self.popup.set_target_display(target)
        self._apply_settings()
        self.settings_status.configure(text="Ayarlar kaydedildi ve uygulandı ✓", foreground="#15803d")
        self._notify("Ayarlar kaydedildi ve uygulandı ✓")

    def _capture_hotkey(self, variable, label: str) -> None:
        """Klavyeden kısayol yakalar; yakalama sırasında global kısayollar durur."""
        self._pause_hotkeys()
        try:
            dialog = HotkeyCaptureDialog(self.root, (variable.get() or "").strip())
            spec = dialog.show()
            if spec:
                variable.set(spec)
                self.settings_status.configure(
                    text=f"{label} alındı: {spec} — uygulamak için 'Ayarları Kaydet'e basın.",
                    foreground="#15803d",
                )
        finally:
            self._resume_hotkeys()

    def _reset_settings(self) -> None:
        if not messagebox.askyesno(
            APP_TITLE, "Tüm ayarlar varsayılana dönecek. Devam edilsin mi?"
        ):
            return
        self.config.clear()
        self.config.update(DEFAULT_CONFIG)
        self.store.save_config()
        self._load_settings_vars()
        self.src_combo.set(code_to_label(self.config.get("source_lang", "auto")))
        self.tgt_combo.set(
            code_to_label(self.config.get("target_lang", "tr"), include_auto=False)
        )
        self._apply_settings()
        self.settings_status.configure(text="Varsayılan ayarlar yüklendi.", foreground="#15803d")
        self._notify("Varsayılan ayarlar yüklendi ✓")

    # ==================================================================
    # Sekme: Hakkında
    # ==================================================================
    def _build_about_tab(self) -> None:
        page = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(page, text="Hakkında")

        ttk.Label(page, text=f"{APP_NAME}", font=("Segoe UI Semibold", 16)).pack(
            anchor="w"
        )
        ttk.Label(
            page,
            text=f"Sürüm {APP_VERSION} — masaüstünde seçtiğiniz metni ve ekran bölgelerini çeviren yerel uygulama.",
            foreground="#475569",
        ).pack(anchor="w", pady=(2, 14))

        info = (
            "Kullanım\n"
            "  1. Herhangi bir uygulamada metni seçin.\n"
            "  2. Global kısayola basın (varsayılan: Ctrl+Alt+T).\n"
            "  3. Çeviri, imlecin yanında açılan balonda görünür.\n\n"
            "OCR (Ekrandan Çeviri)\n"
            "  Ayarlar'dan OCR modunu açın ve OCR kısayoluna basın.\n"
            "  Fareyle bir ekran bölgesi seçin; dışı kararır, bölge tanınır ve çevrilir.\n"
            "  Windows OCR motoru kullanılır (dil paketleri gerekir); Tesseract varsa yedektir.\n\n"
            "Balondaki düğmeler: Kopyala • Oku (TTS) • Kelime Kaydet • Kapat\n"
            "Balondaki 'Hedef dil' düğmesiyle aranabilir dil seçici açılır;\n"
            "Türkçe veya İngilizce yazarak dil bulabilirsiniz (örn. 'ing', 'english').\n"
            "⇄ düğmesi çeviri çıktısını kaynak yapıp önceki kaynak dile geri çevirir.\n"
            "Seçim ana uygulama, ayarlar ve sonraki çevirilerle otomatik senkronlanır.\n"
            "Balon sürüklenebilir; X ile veya süre dolunca kapanır.\n\n"
            "Pano İzleme\n"
            "  Ayarlardan açarsanız panoya kopyaladığınız metin otomatik çevrilir.\n\n"
            "Sistem Tepsisi / Arka Plan\n"
            "  X düğmesi uygulamayı KAPATMAZ; sistem tepsisine küçültür ve kısayollar dinlenmeye devam eder.\n"
            "  Açmak: tepsideki QBTranslator simgesine çift tıklayın.\n"
            "  Tamamen kapatmak: simgeye sağ tık → Çıkış veya Ayarlar → 'UYGULAMADAN TAMAMEN ÇIKIŞ'.\n\n"
            "Otomatik Başlatma\n"
            "  Ayarlar'dan 'Windows açılışında otomatik başlat' seçeneği açıkken uygulama\n"
            "  oturum açılışında simge durumunda başlar ve kısayolları dinlemeye devam eder.\n\n"
            "Çeviri Motorları\n"
            "  Varsayılan: Google Translate (API anahtarı gerekmez).\n"
            "  İsteğe bağlı: MyMemory, LibreTranslate, Lingva, LLM (Ollama / LM Studio / OpenAI).\n\n"
            "Gizlilik\n"
            "  Çevrilen metin yalnızca seçtiğiniz çeviri servisine gönderilir.\n"
            "  Geçmiş ve kayıtlı kelimeler yalnızca bu bilgisayarda, data/ klasöründe tutulur.\n"
            "  Uygulama hiçbir analitik veri toplamaz.\n\n"
            "Veri Klasörü\n"
        )
        text = tk.Text(
            page,
            wrap="word",
            font=("Segoe UI", 10),
            relief="flat",
            bg=self.root.cget("bg"),
            height=24,
        )
        text.insert("1.0", info)
        text.insert("end", f"  {DATA_DIR}\n")
        text.configure(state="disabled")
        text.pack(fill="both", expand=True)

    # ==================================================================
    # Çeviri akışı
    # ==================================================================
    def _translate_async(self, text: str, source: str, target: str, context: tuple) -> None:
        config_snapshot = dict(self.config)

        def worker():
            started = time.perf_counter()
            try:
                outcome = translate(text, source, target, config_snapshot)
                elapsed = time.perf_counter() - started
                self.events.put(("translation_ok", context, outcome, elapsed))
            except Exception as error:
                self.events.put(("translation_err", context, str(error)))

        threading.Thread(target=worker, daemon=True, name="TranslateWorker").start()

    def _show_popup_loading(self, text: str) -> TranslationPopup:
        if self.popup and self.popup.alive:
            self.popup.close()
        self.popup = TranslationPopup(self, text, "auto")
        self.popup.show_loading()
        return self.popup

    def _popup_translate(self, text: str) -> None:
        target = self.config.get("target_lang", "tr")
        popup = self._show_popup_loading(text)
        self._popup_seq += 1
        popup.request_id = self._popup_seq
        self._translate_async(
            text, "auto", target, ("popup", self._popup_seq, text, "auto", target)
        )

    def popup_target_changed(self, popup, target_code: str) -> None:
        """Balondaki hedef dil değişti: ayarı kaydet ve metni yeniden çevir."""
        self.set_target_language(target_code)
        if not (popup and popup.alive):
            return
        text = (popup.source_text or "").strip()
        if text:
            self._retranslate_popup(popup, text, "auto", target_code)

    def swap_popup_translation(
        self, popup, text: str, source_lang: str, target_code: str
    ) -> None:
        """Takas düğmesi: çeviri çıktısını yeni kaynak yapıp eski kaynak diline çevirir."""
        self.set_target_language(target_code)
        self._retranslate_popup(popup, text, source_lang, target_code)

    def _retranslate_popup(
        self, popup, text: str, source_lang: str, target_code: str
    ) -> None:
        if not (popup and popup.alive):
            return
        text = (text or "").strip()
        if not text:
            return
        source_lang = source_lang or "auto"
        self._popup_seq += 1
        popup.request_id = self._popup_seq
        popup.show_loading(reposition=False)
        self._translate_async(
            text,
            source_lang,
            target_code,
            ("popup", self._popup_seq, text, source_lang, target_code),
        )

    # ==================================================================
    # Global kısayol / pano olayları
    # ==================================================================
    def _on_hotkey(self) -> None:
        self.events.put(("hotkey",))

    def _capture_worker(self) -> None:
        try:
            self._suppress_clipboard_until = time.time() + 1.6
            text = capture_selected_text(self.config.get("restore_clipboard", True))
            self._suppress_clipboard_until = time.time() + 0.8
            try:
                self.clipboard.sync()
            except Exception:
                pass
            if text:
                self.events.put(("selection_ok", text))
            else:
                self.events.put(("selection_empty",))
        finally:
            self._capturing = False

    # ------------------------------------------------------------------
    # OCR akışı
    # ------------------------------------------------------------------
    def _on_ocr_hotkey(self) -> None:
        self.events.put(("ocr_hotkey",))

    def _start_ocr_selection(self) -> None:
        if not self.config.get("ocr_enabled"):
            self._notify("OCR kapalı. Ayarlar'dan etkinleştirebilirsiniz.")
            return
        if self._ocr_active:
            return
        self._ocr_active = True
        if self.popup and self.popup.alive:
            self.popup.close()
        self._notify("OCR: ekrandan çevrilecek alanı seçin…")
        try:
            self._ocr_selector = ScreenRegionSelector(
                self.root, self._on_ocr_region_selected
            )
        except Exception as error:
            self._ocr_active = False
            self._ocr_selector = None
            self._notify(f"OCR başlatılamadı: {error}")

    def _on_ocr_region_selected(self, region) -> None:
        self._ocr_selector = None
        self._ocr_active = False
        if not region:
            self._notify("OCR iptal edildi.")
            return

        # OCR tamamlanana kadar balon açmıyoruz; aksi halde yükleme balonu
        # ekran görüntüsüne girip OCR sonucunu kirletebilir.
        self._notify("OCR: metin tanınıyor…")
        threading.Thread(
            target=self._ocr_worker, args=(region,), daemon=True, name="OCRWorker"
        ).start()

    def _ocr_worker(self, region) -> None:
        try:
            text, error = recognize_region(*region)
            self.events.put(("ocr_result", text or "", error or ""))
        except Exception as error:
            self.events.put(("ocr_result", "", str(error)))

    def _handle_ocr_result(self, text: str, error: str) -> None:
        if error:
            popup = self._show_popup_loading("")
            popup.show_error(f"OCR hatası:\n{error}")
            self._notify("OCR hatası.")
            return

        text = (text or "").strip()
        if not text:
            popup = self._show_popup_loading("")
            message = (
                "OCR metni tanınamadı.\n\n"
                "Daha büyük veya daha belirgin bir alan seçin; Windows OCR dil paketinin kurulu olduğundan emin olun."
            )
            capture = last_capture_path()
            if capture:
                message += f"\n\nSon ekran görüntüsü (tanı için):\n{capture}"
            popup.show_error(message)
            self._notify("OCR metni tanınamadı.")
            return

        text = text[:5000]
        self._notify("OCR tamamlandı ✓")
        self._popup_translate(text)

    def _on_clipboard_text(self, text: str) -> None:
        if not self.config.get("clipboard_monitor"):
            return
        if time.time() < self._suppress_clipboard_until:
            return
        text = (text or "").strip()
        if len(text) < 2 or len(text) > 5000:
            return
        lowered = text.lower()
        if lowered.startswith(("http://", "https://")) and " " not in text:
            return
        if text == self._last_clipboard_text:
            return
        self._last_clipboard_text = text
        self.events.put(("clipboard_text", text))

    # ==================================================================
    # Olay döngüsü
    # ==================================================================
    def _pump_events(self) -> None:
        while True:
            if self._force_quit:
                return
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            try:
                self._handle_event(event)
            except Exception:
                # Tek bir bozuk olay (ör. bozuk geçmiş kaydı) uygulamayı durdurmasın.
                continue
        if self._force_quit:
            return
        try:
            self.root.after(90, self._pump_events)
        except tk.TclError:
            pass

    def _handle_event(self, event: tuple) -> None:
        kind = event[0]

        if kind == "hotkey":
            if self._capturing:
                return
            self._capturing = True
            threading.Thread(target=self._capture_worker, daemon=True, name="CaptureWorker").start()

        elif kind == "selection_ok":
            self._popup_translate(event[1])

        elif kind == "selection_empty":
            popup = self._show_popup_loading("")
            popup.show_error(
                "Seçili metin yakalanamadı.\n\n"
                "Metni seçip kısayola tekrar basın. Bazı uygulamalar Ctrl+C ile kopyalamayı desteklemez."
            )

        elif kind == "clipboard_text":
            self._popup_translate(event[1])

        elif kind == "tray_show":
            self._show_window()

        elif kind == "tray_quit":
            self._quit_application()

        elif kind == "ocr_hotkey":
            self._start_ocr_selection()

        elif kind == "ocr_result":
            self._handle_ocr_result(event[1], event[2])

        elif kind == "translation_ok":
            _kind, context, outcome, elapsed = event
            self._on_translation_ok(context, outcome, elapsed)

        elif kind == "translation_err":
            _kind, context, message = event
            self._on_translation_error(context, message)

        elif kind == "hotkey_error":
            code = event[1]
            self._set_chip(self.hotkey_chip, "Kısayol kaydedilemedi", ok=False)
            self.settings_status.configure(
                text=f"Kısayol kaydedilemedi (hata {code}). Başka bir uygulama kullanıyor olabilir; farklı bir kombinasyon deneyin.",
                foreground="#b91c1c",
            )

        elif kind == "ocr_hotkey_error":
            code = event[1]
            self._set_chip(self.ocr_chip, "OCR kısayolu kaydedilemedi", ok=False)
            self.settings_status.configure(
                text=f"OCR kısayolu kaydedilemedi (hata {code}). Başka bir uygulama kullanıyor olabilir.",
                foreground="#b91c1c",
            )

    def _on_translation_ok(self, context: tuple, outcome, elapsed: float) -> None:
        kind = context[0]
        if kind == "popup":
            _kind, request_id, source_text, _source, _target = context
            if (
                self.popup
                and self.popup.alive
                and getattr(self.popup, "request_id", None) == request_id
            ):
                self.popup.show_result(outcome)
            self.store.add_history(
                source_text,
                outcome.text,
                outcome.source_lang,
                outcome.target_lang,
                outcome.engine,
            )
            self._reload_history()
        else:
            _kind, text, source, target = context
            self._manual_busy = False
            self.btn_translate.configure(state="normal", text="Çevir  (Ctrl+Enter)")
            self._set_manual_output(outcome.text, error=False)
            self.manual_status.configure(
                text=(
                    f"{outcome.engine_label}  •  {elapsed:.2f} sn  •  "
                    f"{lang_name(outcome.source_lang)} → {lang_name(outcome.target_lang)}"
                ),
                foreground="#15803d",
            )
            self.store.add_history(
                text,
                outcome.text,
                outcome.source_lang,
                outcome.target_lang,
                outcome.engine,
            )
            self._reload_history()

    def _on_translation_error(self, context: tuple, message: str) -> None:
        if context[0] == "popup":
            request_id = context[1]
            if (
                self.popup
                and self.popup.alive
                and getattr(self.popup, "request_id", None) == request_id
            ):
                self.popup.show_error(message)
        else:
            self._manual_busy = False
            self.btn_translate.configure(state="normal", text="Çevir  (Ctrl+Enter)")
            self._set_manual_output(message, error=True)
            self.manual_status.configure(text="Çeviri başarısız.", foreground="#b91c1c")

    # ==================================================================
    # Ortak eylemler
    # ==================================================================
    def copy_to_clipboard(self, text: str) -> None:
        if not text:
            return
        set_clipboard_text(text)
        self._suppress_clipboard_until = time.time() + 0.8
        try:
            self.clipboard.sync()
        except Exception:
            pass

    def speak(self, text: str) -> None:
        if not text:
            return
        rate = self.config.get("tts_rate", 0)
        threading.Thread(
            target=self.tts.speak, args=(text, rate), daemon=True, name="TTSWorker"
        ).start()

    def is_speaking(self) -> bool:
        return self.tts.is_speaking

    def stop_speaking(self) -> None:
        self.tts.stop()

    def save_word(
        self,
        word: str,
        translation: str,
        source_lang: str,
        target_lang: str,
    ) -> bool:
        if not word.strip() or not translation.strip():
            return False
        was_present = any(
            item.get("word", "").casefold() == word.strip().casefold()
            and item.get("translation", "").casefold() == translation.strip().casefold()
            for item in self.store.words
        )
        self.store.add_word(word, translation, source_lang, target_lang)
        self._reload_words()
        return not was_present

    def _open_detail(self, source_text: str, translation: str, meta: str) -> None:
        win = tk.Toplevel(self.root)
        win.title("Çeviri Detayı")
        win.geometry("680x460")
        win.transient(self.root)

        ttk.Label(win, text=meta, foreground="#64748b").pack(anchor="w", padx=14, pady=(12, 6))

        ttk.Label(win, text="Kaynak").pack(anchor="w", padx=14)
        source_box = tk.Text(win, height=6, wrap="word", relief="solid", borderwidth=1, padx=8, pady=6)
        source_box.insert("1.0", source_text)
        source_box.configure(state="disabled")
        source_box.pack(fill="x", padx=14, pady=(2, 10))

        ttk.Label(win, text="Çeviri").pack(anchor="w", padx=14)
        result_box = tk.Text(win, height=8, wrap="word", relief="solid", borderwidth=1, padx=8, pady=6)
        result_box.insert("1.0", translation)
        result_box.configure(state="disabled")
        result_box.pack(fill="both", expand=True, padx=14, pady=(2, 10))

        buttons = ttk.Frame(win)
        buttons.pack(fill="x", padx=14, pady=(0, 12))
        ttk.Button(
            buttons, text="Kopyala", command=lambda: self.copy_to_clipboard(translation)
        ).pack(side="left")
        ttk.Button(buttons, text="Oku", command=lambda: self.speak(translation)).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(buttons, text="Kapat", command=win.destroy).pack(side="right")

    # ==================================================================
    # Ayar uygulama
    # ==================================================================
    def _set_chip(self, label: tk.Label, text: str, ok: bool | None = None) -> None:
        if ok is True:
            bg, fg = "#12352a", "#6ee7b7"
        elif ok is False:
            bg, fg = "#3b1d1d", "#fca5a5"
        else:
            bg, fg = "#1e293b", "#93c5fd"
        label.configure(text=text, bg=bg, fg=fg)

    def _apply_settings(self, initial: bool = False) -> None:
        self._apply_hotkeys(initial=initial)
        self._apply_autostart()
        self._apply_tray()

        # Pano izleme
        want_monitor = bool(self.config.get("clipboard_monitor"))
        if want_monitor and not self.clipboard.is_alive():
            self.clipboard = ClipboardWatcher(self._on_clipboard_text)
            self.clipboard.start()
        elif not want_monitor and self.clipboard.is_alive():
            self.clipboard.stop()
        self._set_chip(
            self.monitor_chip,
            "Pano izleme: açık" if want_monitor else "Pano izleme: kapalı",
            ok=True if want_monitor else None,
        )

        # Durum çubuğu
        self._refresh_status_bar()

    def _apply_hotkeys(self, initial: bool = False) -> None:
        hotkey_spec = self.config.get("hotkey", "ctrl+alt+t")
        translate_ok = True
        try:
            parse_hotkey(hotkey_spec)
            self.hotkey.start(
                hotkey_spec,
                self._on_hotkey,
                lambda code: self.events.put(("hotkey_error", code)),
            )
            self._set_chip(self.hotkey_chip, f"Kısayol: {hotkey_spec}", ok=True)
        except ValueError as exc:
            translate_ok = False
            self._set_chip(self.hotkey_chip, "Kısayol geçersiz", ok=False)
            if initial:
                self.settings_status.configure(
                    text=f"Kısayol hatası: {exc}", foreground="#b91c1c"
                )

        ocr_on = bool(self.config.get("ocr_enabled"))
        ocr_spec = self.config.get("ocr_hotkey", "ctrl+alt+o")
        if ocr_on:
            try:
                parse_hotkey(ocr_spec)
                if translate_ok and ocr_spec.strip().lower() == hotkey_spec.strip().lower():
                    raise ValueError("OCR kısayolu çeviri kısayoluyla aynı olamaz.")
                self.ocr_hotkey_listener.start(
                    ocr_spec,
                    self._on_ocr_hotkey,
                    lambda code: self.events.put(("ocr_hotkey_error", code)),
                )
                self._set_chip(self.ocr_chip, f"OCR: açık ({ocr_spec})", ok=True)
            except ValueError as exc:
                self.ocr_hotkey_listener.stop()
                self._set_chip(self.ocr_chip, "OCR kısayolu geçersiz", ok=False)
                if initial:
                    self.settings_status.configure(
                        text=f"OCR kısayolu hatası: {exc}", foreground="#b91c1c"
                    )
        else:
            self.ocr_hotkey_listener.stop()
            self._set_chip(self.ocr_chip, "OCR: kapalı", ok=None)

    def _apply_autostart(self) -> None:
        if os.environ.get("QB_DISABLE_AUTOSTART") == "1":
            return
        want = bool(self.config.get("autostart", True))
        if not autostart.sync(want):
            self._notify("Windows açılışında başlatma ayarı uygulanamadı.")

    def _apply_tray(self) -> None:
        want = bool(self.config.get("tray_icon", True))
        if want:
            if self.tray is None or not self.tray.available:
                if self.tray is not None:
                    self.tray.stop()
                icon_path = str(
                    Path(__file__).resolve().parent / "assets" / "QBTranslator.ico"
                )
                self.tray = TrayIcon(
                    tooltip="QBTranslator — arka planda çalışıyor",
                    on_show=lambda: self.events.put(("tray_show",)),
                    on_quit=lambda: self.events.put(("tray_quit",)),
                    icon_path=icon_path,
                )
                if not self.tray.start():
                    self.tray = None
                    self._notify(
                        "Sistem tepsi simgesi oluşturulamadı; X uygulamayı kapatır."
                    )
        else:
            if self.tray is not None:
                self.tray.stop()
                self.tray = None

    def _card_bg(self) -> str:
        try:
            value = ttk.Style().lookup("TFrame", "background")
            if value:
                return value
        except tk.TclError:
            pass
        try:
            return self.root.cget("bg")
        except tk.TclError:
            return "#f0f0f0"

    # ------------------------------------------------------------------
    # Arka plan / sistem tepsisi davranışı
    # ------------------------------------------------------------------
    def _on_window_close(self) -> None:
        if self._force_quit or not (self.tray and self.tray.available):
            self._quit_application()
        else:
            self._hide_to_tray()

    def _hide_to_tray(self) -> None:
        if not (self.tray and self.tray.available):
            self.root.iconify()
            self._notify(
                "Sistem tepsi simgesi aktif değil; pencere simge durumuna küçültüldü."
            )
            return
        if self.popup and self.popup.alive:
            self.popup.close()
        self.root.withdraw()
        if not self._tray_hint_shown:
            self.tray.show_balloon(
                "QBTranslator",
                "Arka planda çalışıyor.\n"
                "Açmak için simgeye çift tıklayın; çıkmak için sağ tıklayıp 'Çıkış'ı seçin.",
            )
            self._tray_hint_shown = True

    def _show_window(self) -> None:
        try:
            self.root.deiconify()
            self.root.state("normal")
            self.root.lift()
            self.root.focus_force()
        except tk.TclError:
            pass

    def _confirm_quit(self) -> None:
        if messagebox.askyesno(
            APP_TITLE,
            "Uygulamadan tamamen çıkılsın mı?\nArka plan dinlemesi duracak ve kısayollar devre dışı kalacak.",
        ):
            self._quit_application()

    def _quit_application(self) -> None:
        self._force_quit = True
        self._on_close()

    def _pause_hotkeys(self) -> None:
        self.hotkey.stop()
        self.ocr_hotkey_listener.stop()

    def _resume_hotkeys(self) -> None:
        self._apply_hotkeys()

    def _refresh_status_bar(self) -> None:
        engine_code = self.config.get("engine", "google")
        monitor = "açık" if self.config.get("clipboard_monitor") else "kapalı"
        ocr = "açık" if self.config.get("ocr_enabled") else "kapalı"
        try:
            self.status_engine_label.configure(
                text=(
                    f"Motor: {ENGINE_LABELS.get(engine_code, engine_code)}"
                    f"   •   Hedef: {lang_name(self.config.get('target_lang', 'tr'))}"
                )
            )
            self.status_hotkey_label.configure(
                text=(
                    f"Kısayol: {self.config.get('hotkey')}"
                    f"   •   OCR: {ocr}"
                    f"   •   Pano izleme: {monitor}"
                )
            )
        except tk.TclError:
            pass

    def _notify(self, text: str) -> None:
        """Durum çubuğunda kısa bildirim gösterir, sonra motor bilgisine döner."""
        try:
            self.status_engine_label.configure(text=text)
        except tk.TclError:
            return

        def _restore():
            try:
                self._refresh_status_bar()
            except tk.TclError:
                pass

        try:
            self.root.after(2600, _restore)
        except tk.TclError:
            pass

    # ==================================================================
    # Kapanış
    # ==================================================================
    def _on_close(self) -> None:
        try:
            geometry = self.root.geometry()
            if self._valid_geometry(geometry):
                self.config["window_geometry"] = geometry
            self.store.save_config()
        except Exception:
            pass
        try:
            if self._ocr_selector is not None:
                self._ocr_selector._cancel()
        except Exception:
            pass
        try:
            self.hotkey.stop()
        except Exception:
            pass
        try:
            self.ocr_hotkey_listener.stop()
        except Exception:
            pass
        try:
            self.clipboard.stop()
        except Exception:
            pass
        try:
            self.tts.stop()
        except Exception:
            pass
        try:
            if self.tray is not None:
                self.tray.stop()
                self.tray = None
        except Exception:
            pass
        try:
            clear_last_capture()
        except Exception:
            pass
        if self.popup and self.popup.alive:
            self.popup.close()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
