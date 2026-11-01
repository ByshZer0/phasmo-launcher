"""Tkinter / ttk 主题。"""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

BG = "#0B0D12"
PANEL = "#121722"
PANEL_ALT = "#171D2A"
INPUT_BG = "#0E121B"
BORDER = "#252E40"
BORDER_HOVER = "#35415A"
TEXT = "#E9EDF5"
MUTED = "#8C96AA"
FAINT = "#5F6B82"
ACCENT = "#7CE3A1"
ACCENT_HOVER = "#9AF0B8"
ACCENT_PRESSED = "#5BCB84"
ON_ACCENT = "#07130C"
DANGER = "#FF7B85"
WARNING = "#F4C86A"
INFO = "#78B7FF"
LOG_BG = "#090C12"
LOG_TEXT = "#B8C4D8"


def pick_font(root: tk.Misc) -> str:
    available = set(tkfont.families(root))
    for name in ("Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", "Noto Sans CJK SC"):
        if name in available:
            return name
    return "TkDefaultFont"


def apply_theme(root: tk.Tk) -> str:
    font = pick_font(root)
    root.configure(bg=BG)
    root.option_add("*Font", (font, 10))
    root.option_add("*TCombobox*Listbox.background", PANEL_ALT)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", ON_ACCENT)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", background=BG, foreground=TEXT, font=(font, 10))
    style.configure("TFrame", background=BG)
    style.configure("Panel.TFrame", background=PANEL)
    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("Panel.TLabel", background=PANEL, foreground=TEXT)
    style.configure("Title.TLabel", background=BG, foreground=TEXT, font=(font, 23, "bold"))
    style.configure("Subtitle.TLabel", background=BG, foreground=MUTED, font=(font, 10))
    style.configure("Section.TLabel", background=PANEL, foreground=TEXT, font=(font, 12, "bold"))
    style.configure("Muted.TLabel", background=PANEL, foreground=MUTED, font=(font, 9))
    style.configure("Footer.TLabel", background=BG, foreground=FAINT, font=(font, 9))
    style.configure("StatusTitle.TLabel", background=PANEL, foreground=MUTED, font=(font, 9))
    style.configure("StatusValue.TLabel", background=PANEL, foreground=TEXT, font=(font, 13, "bold"))
    style.configure("StatusDetail.TLabel", background=PANEL, foreground=FAINT, font=(font, 9))
    style.configure("Hint.TLabel", background=BG, foreground=MUTED, font=(font, 9))

    style.configure(
        "Accent.TButton",
        background=ACCENT,
        foreground=ON_ACCENT,
        bordercolor=ACCENT,
        lightcolor=ACCENT,
        darkcolor=ACCENT,
        borderwidth=0,
        focusthickness=0,
        padding=(18, 13),
        font=(font, 13, "bold"),
    )
    style.map(
        "Accent.TButton",
        background=[("disabled", "#304737"), ("pressed", ACCENT_PRESSED), ("active", ACCENT_HOVER)],
        foreground=[("disabled", "#7B8C80")],
    )

    style.configure(
        "Secondary.TButton",
        background=PANEL_ALT,
        foreground=TEXT,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        borderwidth=1,
        focusthickness=0,
        padding=(14, 9),
        font=(font, 10),
    )
    style.map(
        "Secondary.TButton",
        background=[("disabled", "#151A24"), ("pressed", "#20283A"), ("active", "#232C3F")],
        foreground=[("disabled", "#5B657A")],
        bordercolor=[("active", BORDER_HOVER)],
    )

    style.configure(
        "Small.TButton",
        background=PANEL_ALT,
        foreground=MUTED,
        bordercolor=BORDER,
        borderwidth=1,
        focusthickness=0,
        padding=(9, 4),
        font=(font, 9),
    )
    style.map(
        "Small.TButton",
        background=[("active", "#232C3F"), ("pressed", "#20283A")],
        foreground=[("active", TEXT)],
    )

    style.configure(
        "TEntry",
        fieldbackground=INPUT_BG,
        foreground=TEXT,
        insertcolor=TEXT,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        borderwidth=1,
        padding=(8, 5),
    )
    style.map("TEntry", bordercolor=[("focus", ACCENT)], lightcolor=[("focus", ACCENT)])

    style.configure(
        "TSpinbox",
        fieldbackground=INPUT_BG,
        foreground=TEXT,
        arrowcolor=MUTED,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        borderwidth=1,
        padding=(7, 6),
    )
    style.map("TSpinbox", bordercolor=[("focus", ACCENT)])

    style.configure(
        "TCombobox",
        fieldbackground=INPUT_BG,
        background=INPUT_BG,
        foreground=TEXT,
        arrowcolor=MUTED,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        borderwidth=1,
        padding=(8, 6),
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", INPUT_BG)],
        foreground=[("readonly", TEXT)],
        bordercolor=[("focus", ACCENT)],
        selectbackground=[("readonly", INPUT_BG)],
        selectforeground=[("readonly", TEXT)],
    )

    style.configure(
        "TCheckbutton",
        background=PANEL,
        foreground=MUTED,
        indicatorbackground=INPUT_BG,
        indicatorforeground=ACCENT,
        bordercolor=BORDER,
        focuscolor=PANEL,
        padding=(0, 2),
    )
    style.map(
        "TCheckbutton",
        background=[("active", PANEL)],
        foreground=[("active", TEXT)],
        indicatorbackground=[("selected", ACCENT), ("active", INPUT_BG)],
        indicatorforeground=[("selected", ON_ACCENT)],
    )

    style.configure(
        "Vertical.TScrollbar",
        background=PANEL_ALT,
        troughcolor=LOG_BG,
        bordercolor=LOG_BG,
        arrowcolor=MUTED,
        width=11,
    )
    style.map("Vertical.TScrollbar", background=[("active", BORDER_HOVER)])

    return font
