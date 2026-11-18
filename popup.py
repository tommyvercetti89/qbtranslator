"""
popup.py — İmleç konumunda açılan çeviri balonu.

Her zaman üstte, çerçevesiz, sürüklenebilir. Çeviri sonucu, sesli okuma,
kopyalama ve kelime kaydetme düğmelerini içerir.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from langs import code_to_label, is_rtl, lang_name
from langpicker import LanguagePicker

BG = "#141a21"
BG_HEADER = "#1b232d"
BG_BUTTON = "#242e3a"
BG_BUTTON_HOVER = "#2f3c4c"
FG = "#e8eef6"
MUTED = "#93a1b1"
ACCENT = "#4da3ff"
BORDER = "#33404f"
OK_GREEN = "#5ecb8a"
ERR_RED = "#ff7b7b"

FONT_UI = ("Segoe UI", 9)
FONT_TEXT = ("Segoe UI", 11)
FONT_TITLE = ("Segoe UI Semibold", 9)


class TranslationPopup:
    """Tek bir çeviri balonu. Aynı anda yalnızca bir tanesi açık tutulur."""

    def __init__(self, app, source_text: str, source_lang: str = "auto") -> None:
        self.app = app
        self.source_text = source_text or ""
        self.source_lang = source_lang or "auto"
        self.result = None
        self.alive = True
        self._hide_job = None
        self._drag_offset = (0, 0)
        self.target_code = self.app.config.get("target_lang", "tr")
        self._picker = None
        self._selection_active = False
        self._build()

    # ------------------------------------------------------------------
    # Arayüz kurulumu
    # ------------------------------------------------------------------
    def _build(self) -> None:
        self.win = tk.Toplevel(self.app.root)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg=BG)

        outer = tk.Frame(self.win, bg=BG, highlightbackground=BORDER, highlightthickness=1)
        outer.pack(fill="both", expand=True)

        header = tk.Frame(outer, bg=BG_HEADER, padx=12, pady=8)
        header.pack(fill="x")

        self.header_label = tk.Label(
            header,
            text="ÇEVİRİ",
            bg=BG_HEADER,
            fg=MUTED,
            font=FONT_TITLE,
            anchor="w",
        )
        self.header_label.pack(side="left")

        close_button = tk.Label(
            header,
            text="✕",
            bg=BG_HEADER,
            fg=MUTED,
            font=("Segoe UI", 10),
            padx=6,
            cursor="hand2",
        )
        close_button.pack(side="right")
        close_button.bind("<Button-1>", lambda _e: self.close())
        close_button.bind("<Enter>", lambda _e: close_button.configure(fg=ERR_RED))
        close_button.bind("<Leave>", lambda _e: close_button.configure(fg=MUTED))

        # sürükleme
        for widget in (header, self.header_label):
            widget.bind("<Button-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._do_drag)

        body = tk.Frame(outer, bg=BG, padx=12, pady=10)
        body.pack(fill="both", expand=True)

        self.source_label = tk.Label(
            body,
            text=self._trim_source(self.source_text),
            bg=BG,
            fg=MUTED,
            font=FONT_UI,
            justify="left",
            anchor="w",
            wraplength=480,
        )
        self.source_label.pack(fill="x", anchor="w")

        separator = tk.Frame(body, bg=BORDER, height=1)
        separator.pack(fill="x", pady=(8, 8))

        text_frame = tk.Frame(body, bg=BG)
        text_frame.pack(fill="both", expand=True)

        self.text_widget = tk.Text(
            text_frame,
            width=54,
            height=3,
            bg=BG,
            fg=FG,
            font=FONT_TEXT,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            wrap="word",
            cursor="xterm",
            selectbackground=ACCENT,
            selectforeground="#06121f",
            padx=0,
            pady=0,
            spacing1=2,
            spacing3=2,
        )
        self.text_widget.pack(side="left", fill="both", expand=True)
        self.text_widget.configure(state="disabled")
        self.text_widget.bind("<Control-c>", self._copy_selection)

        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.text_widget.yview)
        scrollbar.pack(side="right", fill="y")
        self.text_widget.configure(yscrollcommand=scrollbar.set)

        self.status_label = tk.Label(
            body,
            text="",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 8),
            anchor="w",
        )
        self.status_label.pack(fill="x", pady=(8, 6))

        # --- aranabilir hedef dil seçici ----------------------------
        target_row = tk.Frame(body, bg=BG)
        target_row.pack(fill="x", pady=(0, 6))
        tk.Label(
            target_row,
            text="Hedef dil:",
            bg=BG,
            fg=MUTED,
            font=FONT_UI,
        ).pack(side="left")

        self.target_button = tk.Label(
            target_row,
            text=f"{code_to_label(self.target_code, include_auto=False)}  ▾",
            bg=BG_BUTTON,
            fg=FG,
            font=FONT_UI,
            padx=10,
            pady=4,
            cursor="hand2",
        )
        self.target_button.pack(side="left", padx=(6, 0))
        self.target_button.bind("<Button-1>", lambda _e: self._toggle_language_picker())
        self.target_button.bind(
            "<Enter>", lambda _e: self.target_button.configure(bg=BG_BUTTON_HOVER)
        )
        self.target_button.bind(
            "<Leave>", lambda _e: self.target_button.configure(bg=BG_BUTTON)
        )

        # Takas: çeviri çıktısını kaynak yap, eski kaynak diline geri çevir
        self.swap_button = tk.Label(
            target_row,
            text="⇄",
            bg=BG_BUTTON,
            fg=FG,
            font=("Segoe UI", 12),
            padx=8,
            pady=1,
            cursor="hand2",
        )
        self.swap_button.pack(side="left", padx=(6, 0))
        self.swap_button.bind("<Button-1>", lambda _e: self._swap_languages())
        self.swap_button.bind(
            "<Enter>", lambda _e: self.swap_button.configure(bg=BG_BUTTON_HOVER)
        )
        self.swap_button.bind(
            "<Leave>", lambda _e: self.swap_button.configure(bg=BG_BUTTON)
        )

        buttons = tk.Frame(body, bg=BG)
        buttons.pack(fill="x")

        self.copy_button = self._make_button(buttons, "Kopyala", self._copy_translation)
        self.speak_button = self._make_button(buttons, "Oku", self._speak)
        self.save_button = self._make_button(buttons, "Kelime Kaydet", self._save_word)

        self.close_button = self._make_button(buttons, "Kapat", self.close)
        self.close_button.pack(side="right")

        self.win.bind("<Button-3>", lambda _e: self.close())
        self.win.bind("<Escape>", lambda _e: self.close())
        self.win.bind("<Enter>", lambda _e: self._pause_autohide())
        self.win.bind("<Leave>", lambda _e: self._schedule_autohide())

        self._set_actions_enabled(False)

    def _make_button(self, parent, text: str, command) -> tk.Label:
        button = tk.Label(
            parent,
            text=text,
            bg=BG_BUTTON,
            fg=FG,
            font=FONT_UI,
            padx=10,
            pady=4,
            cursor="hand2",
        )
        button.pack(side="left", padx=(0, 6))
        button.bind("<Button-1>", lambda _e: command())
        button.bind("<Enter>", lambda _e: button.configure(bg=BG_BUTTON_HOVER))
        button.bind("<Leave>", lambda _e: button.configure(bg=BG_BUTTON))
        return button

    # ------------------------------------------------------------------
    # Gösterim durumları
    # ------------------------------------------------------------------
    def show_loading(self, source_text: str | None = None, reposition: bool = True) -> None:
        if source_text is not None:
            self.source_text = source_text
            self.source_label.configure(text=self._trim_source(source_text))
        self.header_label.configure(text="ÇEVİRİLİYOR…")
        self._set_text("…", center=True)
        self.status_label.configure(text="")
        self._set_actions_enabled(False)
        if reposition:
            self._reveal()
        else:
            self._resize_to_content()
            self._cancel_autohide()

    def set_target_display(self, code: str) -> None:
        if not code or code == "auto":
            return
        self.target_code = code
        try:
            self.target_button.configure(
                text=f"{code_to_label(code, include_auto=False)}  ▾"
            )
        except tk.TclError:
            pass

    def set_source_text(self, text: str) -> None:
        """OCR gibi geç gelen kaynak metinleri günceller."""
        self.source_text = text or ""
        try:
            self.source_label.configure(text=self._trim_source(self.source_text))
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    # Aranabilir dil seçici
    # ------------------------------------------------------------------
    def _toggle_language_picker(self) -> None:
        if self._picker is not None:
            try:
                if not self._picker.closed:
                    self._picker.close()
                    return
            except Exception:
                pass
            self._picker = None
        self._open_language_picker()

    def _open_language_picker(self) -> None:
        self._pause_autohide()
        self._selection_active = True
        self._picker = LanguagePicker(
            self.win,
            self.target_button,
            self.target_code,
            on_select=self._on_language_picked,
            on_close=self._on_picker_closed,
        )

    def _on_language_picked(self, code: str) -> None:
        self._picker = None
        self._selection_active = False
        self.set_target_display(code)
        self.app.popup_target_changed(self, code)

    def _on_picker_closed(self) -> None:
        self._picker = None
        self._selection_active = False
        self._schedule_autohide()

    # ------------------------------------------------------------------
    # Kaynak/hedef takası (ileri-geri çeviri)
    # ------------------------------------------------------------------
    def _swap_languages(self) -> None:
        if not self.result:
            return
        detected = (self.result.source_lang or "").strip()
        if not detected or detected == "auto":
            self._flash_button(self.swap_button, "?")
            return

        if self._picker is not None:
            try:
                self._picker.close()
            except Exception:
                pass
            self._picker = None
            self._selection_active = False

        new_source_text = self.result.text
        new_source_lang = self.result.target_lang  # eski hedef dil
        new_target = detected                    # eski kaynak dil

        self.source_text = new_source_text
        self.source_lang = new_source_lang
        self.source_label.configure(text=self._trim_source(new_source_text))
        self.result = None
        self.set_target_display(new_target)
        self.app.swap_popup_translation(
            self, new_source_text, new_source_lang, new_target
        )

    def show_result(self, outcome) -> None:
        self.result = outcome
        self._set_text(outcome.text)
        source_name = lang_name(outcome.source_lang) if outcome.source_lang else "?"
        parts = [f"{source_name} → {lang_name(outcome.target_lang)}", outcome.engine_label]
        self.status_label.configure(text="   •   ".join(parts), fg=MUTED)
        self.header_label.configure(text="ÇEVİRİ")
        self._set_actions_enabled(True)
        self._apply_direction(outcome.target_lang)
        self._resize_to_content()
        self._schedule_autohide()

    def show_error(self, message: str) -> None:
        self.result = None
        self.header_label.configure(text="ÇEVİRİ")
        self.status_label.configure(text="Hata", fg=ERR_RED)
        self._set_text(message, error=True)
        self._set_actions_enabled(False)
        self._resize_to_content()
        self._schedule_autohide()

    def close(self) -> None:
        if not self.alive:
            return
        self.alive = False
        self._cancel_autohide()
        picker = self._picker
        self._picker = None
        self._selection_active = False
        if picker is not None:
            try:
                picker.close()
            except Exception:
                pass
        try:
            self.win.destroy()
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    # Yardımcılar
    # ------------------------------------------------------------------
    def _reveal(self) -> None:
        self.win.update_idletasks()
        width = 540
        height = self.win.winfo_reqheight()
        try:
            from win32util import get_cursor_pos

            cursor_x, cursor_y = get_cursor_pos()
        except Exception:
            cursor_x = self.app.root.winfo_pointerx()
            cursor_y = self.app.root.winfo_pointery()

        screen_w = self.win.winfo_screenwidth()
        screen_h = self.win.winfo_screenheight()

        pos_x = min(max(12, cursor_x + 18), max(12, screen_w - width - 12))
        pos_y = cursor_y + 26
        if pos_y + height > screen_h - 48:
            pos_y = max(12, cursor_y - height - 20)

        self.win.geometry(f"{width}x{height}+{int(pos_x)}+{int(pos_y)}")
        self.win.deiconify()
        self.win.lift()
        self._cancel_autohide()

    def _set_text(self, text: str, error: bool = False, center: bool = False) -> None:
        self.text_widget.configure(state="normal")
        self.text_widget.delete("1.0", "end")
        self.text_widget.insert("1.0", text)
        self.text_widget.tag_configure("error", foreground=ERR_RED)
        if error:
            self.text_widget.tag_add("error", "1.0", "end")
        self.text_widget.configure(state="disabled")

        newline_count = max(1, text.count("\n") + 1)
        wrapped = max(1, (len(text) // 56) + 1)
        lines = max(2, min(12, newline_count + wrapped - 1)) if not center else 1
        self.text_widget.configure(height=lines)

    def _resize_to_content(self) -> None:
        """İçerik değişince pencerenin yüksekliğini yeniden hesaplar."""
        if not self.alive:
            return
        try:
            self.win.update_idletasks()
            width = 540
            height = self.win.winfo_reqheight()
            pos_x = self.win.winfo_x()
            pos_y = self.win.winfo_y()
            screen_h = self.win.winfo_screenheight()
            if pos_y + height > screen_h - 48:
                pos_y = max(12, screen_h - height - 48)
            self.win.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
        except tk.TclError:
            pass

    def _set_actions_enabled(self, enabled: bool) -> None:
        state_fg = FG if enabled else "#5b6674"
        state_bg = BG_BUTTON if enabled else "#1b2128"
        cursor = "hand2" if enabled else "arrow"
        for button in (self.copy_button, self.speak_button, self.save_button):
            button.configure(fg=state_fg, bg=state_bg, cursor=cursor)
            button.unbind("<Button-1>")
            button.unbind("<Enter>")
            button.unbind("<Leave>")
            if enabled:
                if button is self.copy_button:
                    callback = self._copy_translation
                elif button is self.speak_button:
                    callback = self._speak
                else:
                    callback = self._save_word
                button.bind("<Button-1>", lambda _e, cb=callback: cb())
                button.bind("<Enter>", lambda _e, b=button: b.configure(bg=BG_BUTTON_HOVER))
                button.bind("<Leave>", lambda _e, b=button: b.configure(bg=BG_BUTTON))

    def _apply_direction(self, target_lang: str) -> None:
        rtl = is_rtl(target_lang)
        try:
            self.text_widget.tag_configure(
                "direction", justify="right" if rtl else "left"
            )
            self.text_widget.tag_add("direction", "1.0", "end")
        except tk.TclError:
            pass
        self.source_label.configure(
            anchor="e" if rtl else "w", justify="right" if rtl else "left"
        )

    def _trim_source(self, text: str) -> str:
        text = " ".join((text or "").split())
        if len(text) > 320:
            text = text[:317] + "…"
        return text

    # ------------------------------------------------------------------
    # Düğme eylemleri
    # ------------------------------------------------------------------
    def _copy_translation(self) -> None:
        if not self.result:
            return
        self.app.copy_to_clipboard(self.result.text)
        self._flash_button(self.copy_button, "Kopyalandı ✓")

    def _copy_selection(self, _event=None):
        try:
            selected = self.text_widget.get("sel.first", "sel.last")
        except tk.TclError:
            selected = ""
        if selected:
            self.app.copy_to_clipboard(selected)
        return "break"

    def _speak(self) -> None:
        if not self.result:
            return
        if self.app.is_speaking():
            self.app.stop_speaking()
            self._flash_button(self.speak_button, "Durduruldu")
        else:
            self.app.speak(self.result.text)
            self._flash_button(self.speak_button, "Okunuyor…")

    def _save_word(self) -> None:
        if not self.result:
            return
        saved = self.app.save_word(
            self.source_text,
            self.result.text,
            self.result.source_lang or self.source_lang,
            self.result.target_lang,
        )
        if saved:
            self._flash_button(self.save_button, "Kaydedildi ✓")
        else:
            self._flash_button(self.save_button, "Zaten kayıtlı")

    def _flash_button(self, button: tk.Label, text: str, duration: int = 1400) -> None:
        original = button.cget("text")

        def _restore():
            try:
                button.configure(text=original, fg=FG)
            except tk.TclError:
                pass

        button.configure(text=text, fg=OK_GREEN)
        try:
            button.after(duration, _restore)
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    # Sürükleme ve otomatik kapanma
    # ------------------------------------------------------------------
    def _start_drag(self, event) -> None:
        self._drag_offset = (event.x_root - self.win.winfo_x(), event.y_root - self.win.winfo_y())

    def _do_drag(self, event) -> None:
        pos_x = event.x_root - self._drag_offset[0]
        pos_y = event.y_root - self._drag_offset[1]
        self.win.geometry(f"+{int(pos_x)}+{int(pos_y)}")

    def _schedule_autohide(self) -> None:
        self._cancel_autohide()
        # Dil seçimi açıkken balon kapanmasın.
        if self._selection_active or not self.alive:
            return
        try:
            seconds = int(self.app.config.get("popup_autohide_seconds") or 0)
        except (TypeError, ValueError):
            seconds = 0
        if seconds > 0 and self.alive:
            self._hide_job = self.win.after(seconds * 1000, self.close)

    def _cancel_autohide(self) -> None:
        if self._hide_job is not None:
            try:
                self.win.after_cancel(self._hide_job)
            except tk.TclError:
                pass
            self._hide_job = None

    def _pause_autohide(self) -> None:
        self._cancel_autohide()

    def _on_destroy(self) -> None:
        self.alive = False
        self._cancel_autohide()
