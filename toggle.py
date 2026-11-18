"""
toggle.py — iOS tarzı gradyan açma/kapama anahtarı (Canvas tabanlı).

Ek paket gerekmez; ttk.Checkbutton yerine görsel olarak belirgin,
yeşil→turkuaz gradyanlı anahtarlar üretir.
"""

from __future__ import annotations

import tkinter as tk

ON_START = (52, 199, 89)     # #34C759
ON_END = (0, 199, 190)       # #00C7BE
OFF_COLOR = "#cbd5e1"
KNOB_COLOR = "#ffffff"
KNOB_OUTLINE = "#f1f5f9"
KNOB_SHADOW = "#d1d5db"


def _blend(color_a, color_b, t: float) -> str:
    t = max(0.0, min(1.0, t))
    red = int(color_a[0] + (color_b[0] - color_a[0]) * t)
    green = int(color_a[1] + (color_b[1] - color_a[1]) * t)
    blue = int(color_a[2] + (color_b[2] - color_a[2]) * t)
    return f"#{red:02x}{green:02x}{blue:02x}"


class ToggleSwitch(tk.Canvas):
    def __init__(
        self,
        parent,
        variable: tk.IntVar,
        command=None,
        bg: str | None = None,
        width: int = 54,
        height: int = 30,
    ) -> None:
        parent_bg = bg or _parent_bg(parent)
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=parent_bg,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self.var = variable
        self.command = command
        self.w = width
        self.h = height
        self._pos = 1.0 if variable.get() else 0.0
        self._anim_job = None
        self._trace = variable.trace_add("write", self._var_changed)
        self.bind("<Button-1>", self._toggle)
        self._draw(self._pos, self._pos > 0.5)

    def _var_changed(self, *_args) -> None:
        try:
            target = 1.0 if self.var.get() else 0.0
        except tk.TclError:
            return
        if abs(self._pos - target) < 0.001 and self._anim_job is None:
            return
        self._animate(target)

    def _toggle(self, _event=None) -> None:
        target = 0 if self.var.get() else 1
        self.var.set(target)
        if self.command:
            try:
                self.command()
            except Exception:
                pass

    def _animate(self, target: float) -> None:
        if self._anim_job is not None:
            try:
                self.after_cancel(self._anim_job)
            except tk.TclError:
                pass
            self._anim_job = None
        start = self._pos
        steps = 6

        def step(index: int) -> None:
            try:
                fraction = index / steps
                eased = 1 - (1 - fraction) ** 3
                position = start + (target - start) * eased
                self._draw(position, target > 0.5)
                if index < steps:
                    self._anim_job = self.after(14, lambda: step(index + 1))
                else:
                    self._pos = target
                    self._anim_job = None
            except tk.TclError:
                self._anim_job = None

        step(1)

    def destroy(self) -> None:
        """Tk değişken izini bırak; kapanışta hayalet callback kalmasın."""
        try:
            self.var.trace_remove("write", self._trace)
        except Exception:
            pass
        if self._anim_job is not None:
            try:
                self.after_cancel(self._anim_job)
            except tk.TclError:
                pass
            self._anim_job = None
        super().destroy()

    def _draw(self, position: float, on: bool) -> None:
        self.delete("all")
        height = self.h
        width = self.w
        radius = height / 2

        if on:
            center_start = radius
            center_end = width - radius
            strips = max(1, int(center_end - center_start))
            for index in range(strips):
                x = center_start + index
                color = _blend(ON_START, ON_END, index / strips)
                self.create_line(x, 2, x, height - 2, fill=color)
            self.create_oval(
                1, 1, height - 1, height - 1, fill=_blend(ON_START, ON_END, 0.0), outline=""
            )
            self.create_oval(
                width - height + 1,
                1,
                width - 1,
                height - 1,
                fill=_blend(ON_START, ON_END, 1.0),
                outline="",
            )
        else:
            self.create_oval(1, 1, height - 1, height - 1, fill=OFF_COLOR, outline="")
            self.create_oval(
                width - height + 1, 1, width - 1, height - 1, fill=OFF_COLOR, outline=""
            )
            self.create_rectangle(
                radius, 1, width - radius, height - 1, fill=OFF_COLOR, outline=""
            )

        knob = height - 8
        knob_x = 4 + (width - knob - 8) * position
        knob_y = 4
        self.create_oval(
            knob_x + 1,
            knob_y + 1,
            knob_x + knob + 1,
            knob_y + knob + 1,
            fill=KNOB_SHADOW,
            outline="",
        )
        self.create_oval(
            knob_x,
            knob_y,
            knob_x + knob,
            knob_y + knob,
            fill=KNOB_COLOR,
            outline=KNOB_OUTLINE,
        )


class ToggleRow(tk.Frame):
    """Anahtar + açıklama satırı; metne tıklamak da anahtarı çevirir."""

    def __init__(
        self,
        parent,
        text: str,
        variable: tk.IntVar,
        bg: str | None = None,
        font=("Segoe UI", 10),
        wraplength: int = 780,
    ) -> None:
        parent_bg = bg or _parent_bg(parent)
        super().__init__(parent, bg=parent_bg)
        self.switch = ToggleSwitch(self, variable, bg=parent_bg)
        self.switch.pack(side="left", anchor="n")
        self.label = tk.Label(
            self,
            text=text,
            bg=parent_bg,
            fg="#0f172a",
            font=font,
            anchor="w",
            justify="left",
            wraplength=wraplength,
            cursor="hand2",
        )
        self.label.pack(side="left", padx=(10, 0), fill="x", expand=True)
        self.configure(cursor="hand2")
        self.bind("<Button-1>", self._click)
        self.label.bind("<Button-1>", self._click)

    def _click(self, _event=None) -> None:
        self.switch._toggle()


def _parent_bg(parent) -> str:
    try:
        value = parent.cget("background")
        if value:
            return value
    except Exception:
        pass
    try:
        from tkinter import ttk

        value = ttk.Style().lookup("TFrame", "background")
        if value:
            return value
    except Exception:
        pass
    return "#f0f0f0"
