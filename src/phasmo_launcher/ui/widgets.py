"""可复用的界面小部件。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .theme import ACCENT, BORDER, DANGER, FAINT, INFO, MUTED, PANEL, TEXT, WARNING

_STATE_COLORS = {
    "ok": ACCENT,
    "warn": WARNING,
    "error": DANGER,
    "info": INFO,
    "idle": FAINT,
    "neutral": MUTED,
}


class StatusCard(tk.Frame):
    """一张状态卡：顶部圆点 + 标题，下面是状态和详情。"""

    def __init__(self, master: tk.Misc, title: str, detail_width: int = 250) -> None:
        super().__init__(
            master,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
            height=96,
        )
        self.grid_propagate(False)
        self.columnconfigure(1, weight=1)

        self._dot = tk.Canvas(
            self, width=12, height=12, bg=PANEL, highlightthickness=0, bd=0
        )
        self._dot.grid(row=0, column=0, padx=(13, 7), pady=(11, 0), sticky="w")
        self._dot_id = self._dot.create_oval(2, 2, 10, 10, fill=FAINT, outline=FAINT)

        ttk.Label(self, text=title, style="StatusTitle.TLabel").grid(
            row=0, column=1, columnspan=2, padx=(0, 12), pady=(9, 0), sticky="w"
        )

        self._value = ttk.Label(self, text="检测中…", style="StatusValue.TLabel")
        self._value.grid(row=1, column=1, columnspan=2, padx=(0, 12), pady=(1, 0), sticky="w")

        self._detail = ttk.Label(
            self,
            text="",
            style="StatusDetail.TLabel",
            wraplength=detail_width,
            justify="left",
        )
        self._detail.grid(row=2, column=1, columnspan=2, padx=(0, 12), pady=(0, 8), sticky="w")

    def set_state(self, state: str, value: str, detail: str = "") -> None:
        color = _STATE_COLORS.get(state, MUTED)
        self._dot.itemconfigure(self._dot_id, fill=color, outline=color)
        self._value.configure(text=value, foreground=color if state != "neutral" else TEXT)
        self._detail.configure(text=detail)
