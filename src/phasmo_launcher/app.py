"""图形界面。"""

from __future__ import annotations

import ctypes
import logging
import os
import queue
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from . import accelerator
from .accelerator import AcceleratorSpec
from .config import AppConfig, ConfigStore
from .constants import (
    APP_NAME,
    APP_NAME_EN,
    GAME_NAME_CN,
    LAUNCH_ORDER_ACCELERATOR_FIRST,
    LAUNCH_ORDER_STEAM_FIRST,
    MAX_ACCELERATOR_WAIT,
    STEAM_APP_ID,
    VERSION,
)
from .launcher import LaunchMode, LaunchResult, LauncherService
from .logging_setup import setup_logging
from .paths import app_data_dir, log_dir, open_in_explorer, resource_path
from .steam import SteamEnvironment, detect_environment
from .ui import theme
from .ui.theme import apply_theme
from .ui.widgets import StatusCard

logger = logging.getLogger(__name__)

ORDER_LABELS = {
    LAUNCH_ORDER_ACCELERATOR_FIRST: "先加速器，后 Steam",
    LAUNCH_ORDER_STEAM_FIRST: "先 Steam，后加速器",
}
LABEL_TO_ORDER = {value: key for key, value in ORDER_LABELS.items()}


class LauncherApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.logger = setup_logging()
        self.store = ConfigStore()
        self.config = self.store.load()
        self.env: SteamEnvironment | None = None

        self._busy = False
        self._closing = False
        self._loading = True
        self._save_job: str | None = None
        self._queue: queue.Queue[tuple[Callable[..., Any], tuple[Any, ...]]] = queue.Queue()
        self._action_buttons: list[ttk.Button] = []

        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.minsize(900, 660)
        self.root.geometry("960x720")
        self._set_window_icon()
        self.font = apply_theme(self.root)

        self._build_ui()
        self._load_config()
        self._bind_settings()
        self._center_window()
        self._enable_dark_title_bar()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._drain_queue)
        self.root.after(150, lambda: self.refresh_environment(initial=True))

    # ------------------------------------------------------------------
    # 构建界面
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root)
        outer.pack(fill="both", expand=True, padx=22, pady=(16, 10))
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(4, weight=1)

        self._build_header(outer)
        self._build_status(outer)
        self._build_actions(outer)
        self._build_settings(outer)
        self._build_log(outer)
        self._build_footer(outer)

    def _build_header(self, parent: ttk.Frame) -> None:
        header = ttk.Frame(parent)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        accent = tk.Frame(header, bg=theme.ACCENT, width=4, height=46)
        accent.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(0, 12))
        accent.grid_propagate(False)

        ttk.Label(header, text=APP_NAME, style="Title.TLabel").grid(
            row=0, column=1, sticky="w"
        )
        ttk.Label(
            header,
            text=f"{APP_NAME_EN}  ·  Steam 加速器与游戏一键编排",
            style="Subtitle.TLabel",
        ).grid(row=1, column=1, sticky="w", pady=(1, 0))

        right = ttk.Frame(header)
        right.grid(row=0, column=2, rowspan=2, sticky="e")
        tk.Label(
            right,
            text=f"v{VERSION}",
            bg=theme.PANEL,
            fg=theme.MUTED,
            font=(self.font, 9),
            padx=9,
            pady=3,
        ).pack(side="left", padx=(0, 8))
        self.btn_refresh = ttk.Button(
            right, text="↻  重新检测", style="Secondary.TButton", command=self.refresh_environment
        )
        self.btn_refresh.pack(side="left")
        self._action_buttons.append(self.btn_refresh)

    def _build_status(self, parent: ttk.Frame) -> None:
        row = ttk.Frame(parent)
        row.grid(row=1, column=0, sticky="ew", pady=(14, 12))
        for column in range(3):
            row.columnconfigure(column, weight=1, uniform="status")

        self.card_steam = StatusCard(row, "STEAM 客户端")
        self.card_steam.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.card_game = StatusCard(row, f"{GAME_NAME_CN} / PHASMOPHOBIA")
        self.card_game.grid(row=0, column=1, sticky="nsew", padx=6)
        self.card_accel = StatusCard(row, "网络加速器")
        self.card_accel.grid(row=0, column=2, sticky="nsew", padx=(6, 0))

    def _build_actions(self, parent: ttk.Frame) -> None:
        box = ttk.Frame(parent)
        box.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        box.columnconfigure(0, weight=1)

        self.btn_all = ttk.Button(
            box,
            text="▶   一键启动  ·  加速器 + Steam + 恐鬼症",
            style="Accent.TButton",
            command=lambda: self._launch(LaunchMode.ALL),
        )
        self.btn_all.grid(row=0, column=0, sticky="ew")
        self._action_buttons.append(self.btn_all)

        sub = ttk.Frame(box)
        sub.grid(row=1, column=0, sticky="ew", pady=(7, 0))
        sub.columnconfigure(0, weight=1)

        self.order_hint = ttk.Label(sub, text="", style="Hint.TLabel")
        self.order_hint.grid(row=0, column=0, sticky="w")

        buttons = ttk.Frame(sub)
        buttons.grid(row=0, column=1, sticky="e")
        self.btn_game = ttk.Button(
            buttons,
            text="仅启动恐鬼症",
            style="Secondary.TButton",
            command=lambda: self._launch(LaunchMode.GAME),
        )
        self.btn_game.pack(side="left", padx=(0, 6))
        self.btn_steam = ttk.Button(
            buttons,
            text="仅启动 Steam",
            style="Secondary.TButton",
            command=lambda: self._launch(LaunchMode.STEAM),
        )
        self.btn_steam.pack(side="left", padx=(0, 6))
        self.btn_accel = ttk.Button(
            buttons,
            text="测试加速器",
            style="Secondary.TButton",
            command=self._test_accelerator,
        )
        self.btn_accel.pack(side="left")
        self._action_buttons.extend([self.btn_game, self.btn_steam, self.btn_accel])

    def _build_settings(self, parent: ttk.Frame) -> None:
        border = tk.Frame(parent, bg=theme.BORDER)
        border.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        card = tk.Frame(border, bg=theme.PANEL)
        card.pack(fill="both", expand=True, padx=1, pady=1)

        inner = ttk.Frame(card, style="Panel.TFrame")
        inner.pack(fill="both", expand=True, padx=14, pady=(8, 8))
        inner.columnconfigure(0, weight=1)

        title_row = ttk.Frame(inner, style="Panel.TFrame")
        title_row.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        title_row.columnconfigure(0, weight=1)
        ttk.Label(title_row, text="启动设置", style="Section.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.save_hint = ttk.Label(
            title_row, text="修改后自动保存", style="Muted.TLabel"
        )
        self.save_hint.grid(row=0, column=1, sticky="e")

        form = ttk.Frame(inner, style="Panel.TFrame")
        form.grid(row=1, column=0, sticky="ew")
        form.columnconfigure(1, weight=1)

        self.steam_var = tk.StringVar()
        self.accel_var = tk.StringVar()
        self.args_var = tk.StringVar()
        self.wait_var = tk.StringVar()
        self.order_var = tk.StringVar()
        self.close_var = tk.BooleanVar()

        self._label(form, "Steam 目录", 0)
        self.steam_entry = ttk.Entry(form, textvariable=self.steam_var)
        self.steam_entry.grid(row=0, column=1, sticky="ew", padx=(0, 6), pady=3)
        self.btn_browse_steam = ttk.Button(
            form, text="浏览", style="Small.TButton", command=self._browse_steam
        )
        self.btn_browse_steam.grid(row=0, column=2, padx=(0, 6), pady=3)
        self.btn_auto_steam = ttk.Button(
            form, text="自动检测", style="Small.TButton", command=self._auto_detect_steam
        )
        self.btn_auto_steam.grid(row=0, column=3, pady=3)
        self._action_buttons.append(self.btn_auto_steam)

        self._label(form, "加速器程序", 1)
        self.accel_entry = ttk.Entry(form, textvariable=self.accel_var)
        self.accel_entry.grid(row=1, column=1, sticky="ew", padx=(0, 6), pady=3)
        self.btn_browse_accel = ttk.Button(
            form, text="浏览", style="Small.TButton", command=self._browse_accelerator
        )
        self.btn_browse_accel.grid(row=1, column=2, padx=(0, 6), pady=3)
        self.btn_clear_accel = ttk.Button(
            form, text="清除", style="Small.TButton", command=self._clear_accelerator
        )
        self.btn_clear_accel.grid(row=1, column=3, pady=3)
        self._action_buttons.extend(
            [self.btn_browse_steam, self.btn_browse_accel, self.btn_clear_accel]
        )

        self._label(form, "启动参数", 2)
        self.args_entry = ttk.Entry(form, textvariable=self.args_var)
        self.args_entry.grid(row=2, column=1, columnspan=3, sticky="ew", pady=3)

        self._label(form, "等待时间", 3)
        controls = ttk.Frame(form, style="Panel.TFrame")
        controls.grid(row=3, column=1, columnspan=3, sticky="ew", pady=3)
        self.wait_spin = ttk.Spinbox(
            controls,
            from_=0,
            to=MAX_ACCELERATOR_WAIT,
            increment=1,
            width=5,
            textvariable=self.wait_var,
        )
        self.wait_spin.pack(side="left")
        ttk.Label(controls, text="秒", style="Panel.TLabel").pack(side="left", padx=(5, 18))
        ttk.Label(controls, text="启动顺序", style="Panel.TLabel").pack(side="left", padx=(0, 7))
        self.order_combo = ttk.Combobox(
            controls,
            textvariable=self.order_var,
            values=list(ORDER_LABELS.values()),
            state="readonly",
            width=20,
        )
        self.order_combo.pack(side="left")
        self.close_check = ttk.Checkbutton(
            controls,
            text="启动后关闭启动器",
            variable=self.close_var,
            command=self._settings_changed,
        )
        self.close_check.pack(side="left", padx=(18, 0))

        ttk.Label(
            inner,
            text="Steam 目录留空时自动检测；加速器需先在客户端内为 Steam 和恐鬼症开启加速。",
            style="Muted.TLabel",
        ).grid(row=2, column=0, sticky="w", pady=(4, 0))

    def _build_log(self, parent: ttk.Frame) -> None:
        border = tk.Frame(parent, bg=theme.BORDER)
        border.grid(row=4, column=0, sticky="nsew")
        card = tk.Frame(border, bg=theme.PANEL)
        card.pack(fill="both", expand=True, padx=1, pady=1)

        inner = ttk.Frame(card, style="Panel.TFrame")
        inner.pack(fill="both", expand=True, padx=14, pady=(9, 10))
        inner.columnconfigure(0, weight=1)
        inner.rowconfigure(1, weight=1)

        head = ttk.Frame(inner, style="Panel.TFrame")
        head.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        head.columnconfigure(0, weight=1)
        ttk.Label(head, text="运行日志", style="Section.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(
            head, text="清空", style="Small.TButton", command=self._clear_log
        ).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(
            head, text="打开日志目录", style="Small.TButton", command=self._open_log_dir
        ).grid(row=0, column=2)

        text_frame = tk.Frame(inner, bg=theme.LOG_BG)
        text_frame.grid(row=1, column=0, sticky="nsew")
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        self.log_text = tk.Text(
            text_frame,
            height=5,
            wrap="word",
            bg=theme.LOG_BG,
            fg=theme.LOG_TEXT,
            insertbackground=theme.TEXT,
            selectbackground=theme.BORDER_HOVER,
            relief="flat",
            bd=0,
            padx=9,
            pady=6,
            font=("Consolas", 9),
            state="disabled",
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(
            text_frame, orient="vertical", command=self.log_text.yview
        )
        scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.tag_configure("time", foreground=theme.FAINT)
        self.log_text.tag_configure("info", foreground=theme.LOG_TEXT)
        self.log_text.tag_configure("ok", foreground=theme.ACCENT)
        self.log_text.tag_configure("warn", foreground=theme.WARNING)
        self.log_text.tag_configure("error", foreground=theme.DANGER)
        self.log_text.tag_configure("muted", foreground=theme.MUTED)

    def _build_footer(self, parent: ttk.Frame) -> None:
        footer = ttk.Frame(parent)
        footer.grid(row=5, column=0, sticky="ew", pady=(8, 0))
        footer.columnconfigure(0, weight=1)

        self.footer_var = tk.StringVar(value=f"配置：{self.store.path}")
        ttk.Label(
            footer,
            textvariable=self.footer_var,
            style="Footer.TLabel",
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ttk.Button(
            footer, text="打开配置目录", style="Small.TButton", command=self._open_config_dir
        ).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(
            footer, text="保存设置", style="Small.TButton", command=lambda: self._save(show_hint=True)
        ).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(footer, text="退出", style="Small.TButton", command=self._on_close).grid(
            row=0, column=3
        )

    @staticmethod
    def _shorten(value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        return "…" + value[-(limit - 1) :]

    @staticmethod
    def _label(parent: ttk.Frame, text: str, row: int) -> None:
        ttk.Label(parent, text=text, style="Panel.TLabel", width=11).grid(
            row=row, column=0, sticky="w", pady=3
        )

    # ------------------------------------------------------------------
    # 配置
    # ------------------------------------------------------------------
    def _load_config(self) -> None:
        config = self.config.normalized()
        self.steam_var.set(config.steam_path)
        self.accel_var.set(config.accelerator_path)
        self.args_var.set(config.accelerator_args)
        self.wait_var.set(str(config.accelerator_wait_seconds))
        self.order_var.set(ORDER_LABELS.get(config.launch_order, ORDER_LABELS[LAUNCH_ORDER_ACCELERATOR_FIRST]))
        self.close_var.set(config.close_after_launch)
        self._loading = False
        self._update_order_hint()

    def _bind_settings(self) -> None:
        for var in (self.steam_var, self.accel_var, self.args_var, self.wait_var, self.order_var):
            var.trace_add("write", self._settings_changed)

    def _settings_changed(self, *_args: object) -> None:
        if self._loading:
            return
        try:
            wait = int(self.wait_var.get())
        except ValueError:
            wait = self.config.accelerator_wait_seconds
        wait = max(0, min(MAX_ACCELERATOR_WAIT, wait))
        order = LABEL_TO_ORDER.get(self.order_var.get(), LAUNCH_ORDER_ACCELERATOR_FIRST)
        self.config = AppConfig(
            steam_path=self.steam_var.get().strip(),
            accelerator_path=self.accel_var.get().strip(),
            accelerator_args=self.args_var.get().strip(),
            accelerator_wait_seconds=wait,
            launch_order=order,
            close_after_launch=bool(self.close_var.get()),
        ).normalized()
        self._update_order_hint()
        self._update_accelerator_card()
        self.save_hint.configure(text="正在保存…", foreground=theme.MUTED)
        if self._save_job is not None:
            try:
                self.root.after_cancel(self._save_job)
            except tk.TclError:
                pass
        self._save_job = self.root.after(600, self._save)

    def _save(self, *, show_hint: bool = False) -> None:
        self._save_job = None
        try:
            self.store.save(self.config)
        except OSError as exc:
            self.logger.exception("保存配置失败")
            self.save_hint.configure(text="保存失败", foreground=theme.DANGER)
            if show_hint:
                messagebox.showerror("保存失败", f"无法写入配置文件：\n{exc}", parent=self.root)
            return
        self.save_hint.configure(text="已保存", foreground=theme.ACCENT)
        if show_hint:
            self._log(f"配置已保存：{self.store.path}", "ok")

    # ------------------------------------------------------------------
    # 环境检测
    # ------------------------------------------------------------------
    def refresh_environment(self, *, initial: bool = False) -> None:
        if self._busy:
            return
        self._run_async(
            "检测 Steam 与游戏环境",
            lambda: detect_environment(self.config.steam_path or None),
            self._environment_loaded,
            show_error=not initial,
        )

    def _environment_loaded(self, env: SteamEnvironment) -> None:
        self.env = env
        if env.steam_available:
            self.card_steam.set_state("ok", "已就绪", self._shorten(str(env.steam_dir), 38))
        else:
            detail = "请手动选择 Steam 安装目录" if not self.config.steam_path else "手动目录无效，请重新选择"
            self.card_steam.set_state("error", "未找到", detail)

        if env.game_installed:
            self.card_game.set_state(
                "ok",
                "已安装",
                f"AppID {STEAM_APP_ID}  ·  游戏文件已找到",
            )
        else:
            self.card_game.set_state(
                "warn", "未检测到", "请先在 Steam 中安装《恐鬼症》"
            )

        self._update_accelerator_card()

        if env.game_installed and env.steam_available:
            self._log("环境检测完成：Steam 与恐鬼症均已就绪。", "ok")
        elif not env.steam_available:
            self._log("环境检测完成：未找到 Steam。", "warn")
        else:
            self._log("环境检测完成：未找到恐鬼症。", "warn")

    def _update_accelerator_card(self) -> None:
        spec = self._current_spec()
        if not spec.configured:
            self.card_accel.set_state(
                "idle", "未配置", "选择加速器 exe，一键启动时自动拉起"
            )
            return
        error = accelerator.validate_spec(spec)
        if error:
            self.card_accel.set_state("error", "配置无效", self._shorten(error, 42))
            return
        protocol = accelerator.protocol_scheme(spec.path)
        detail = f"系统协议：{protocol}://" if protocol else self._shorten(str(Path(spec.path)), 38)
        self.card_accel.set_state("ok", "已配置", detail)

    # ------------------------------------------------------------------
    # 启动动作
    # ------------------------------------------------------------------
    def _launch(self, mode: LaunchMode) -> None:
        if self._busy:
            return
        self._save()
        if self.env is None:
            messagebox.showinfo(
                "正在检测", "正在检测 Steam 环境，请稍候再试。", parent=self.root
            )
            self.refresh_environment()
            return

        if mode is LaunchMode.ALL and not self.config.accelerator_path:
            if messagebox.askyesno(
                "尚未配置加速器",
                "一键启动会先拉起加速器。\n是否现在选择加速器程序？",
                parent=self.root,
            ):
                self._browse_accelerator()
            if not self.config.accelerator_path:
                return

        if mode in (LaunchMode.ALL, LaunchMode.ACCELERATOR):
            error = accelerator.validate_spec(self._current_spec())
            if error:
                messagebox.showerror("加速器配置有误", error, parent=self.root)
                return

        service = LauncherService()

        def work() -> LaunchResult:
            # 不使用界面缓存的环境，确保用户刚修改的 Steam 路径立即生效。
            return service.run(
                mode,
                self.config,
                progress=lambda message: self._post(self._log, message, "info"),
            )

        self._run_async(
            "执行启动流程",
            work,
            self._launch_finished,
        )

    def _launch_finished(self, result: LaunchResult) -> None:
        for step in result.steps:
            self._log(f"完成：{step}", "ok")
        if result.game_requested:
            self._log("已向 Steam 发送启动请求，游戏窗口稍后出现。", "ok")
        if self.config.close_after_launch:
            self._log("启动器将在 2 秒后关闭。", "muted")
            self.root.after(2000, self._on_close)

    def _test_accelerator(self) -> None:
        if self._busy:
            return
        spec = self._current_spec()
        error = accelerator.validate_spec(spec)
        if error:
            messagebox.showerror("加速器配置有误", error, parent=self.root)
            return

        def work() -> None:
            accelerator.launch(spec)

        self._run_async("测试加速器", work, lambda _: self._log("加速器启动命令已发出。", "ok"))

    def _current_spec(self) -> AcceleratorSpec:
        return AcceleratorSpec(
            path=self.config.accelerator_path,
            args=self.config.accelerator_args,
            wait_seconds=self.config.accelerator_wait_seconds,
        )

    # ------------------------------------------------------------------
    # 文件选择与目录
    # ------------------------------------------------------------------
    def _browse_steam(self) -> None:
        initial = self.config.steam_path or os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        folder = filedialog.askdirectory(
            parent=self.root,
            title="选择 Steam 安装目录（包含 steam.exe）",
            initialdir=initial if Path(initial).is_dir() else None,
        )
        if not folder:
            return
        if not (Path(folder) / "steam.exe").is_file():
            messagebox.showerror(
                "目录无效",
                "所选目录中没有 steam.exe，请选择 Steam 的安装根目录。",
                parent=self.root,
            )
            return
        self.steam_var.set(folder)
        self.refresh_environment()

    def _auto_detect_steam(self) -> None:
        self.steam_var.set("")
        self.refresh_environment()

    def _browse_accelerator(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="选择加速器程序",
            filetypes=[
                ("加速器程序", "*.exe *.com *.lnk"),
                ("可执行文件", "*.exe"),
                ("快捷方式", "*.lnk"),
                ("所有文件", "*.*"),
            ],
        )
        if not path:
            return
        self.accel_var.set(path)

    def _clear_accelerator(self) -> None:
        self.accel_var.set("")

    def _open_config_dir(self) -> None:
        try:
            app_data_dir().mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("无法打开目录", f"无法创建配置目录：\n{exc}", parent=self.root)
            return
        open_in_explorer(app_data_dir())

    def _open_log_dir(self) -> None:
        try:
            log_dir().mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("无法打开目录", f"无法创建日志目录：\n{exc}", parent=self.root)
            return
        open_in_explorer(log_dir())

    # ------------------------------------------------------------------
    # 日志与线程
    # ------------------------------------------------------------------
    def _log(self, message: str, level: str = "info") -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        text = str(message)
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] ", ("time",))
        self.log_text.insert("end", f"{text}\n", (level,))
        line_count = int(self.log_text.index("end-1c").split(".", 1)[0])
        if line_count > 600:
            self.log_text.delete("1.0", f"{line_count - 600}.0")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _post(self, callback: Callable[..., Any], *args: Any) -> None:
        self._queue.put((callback, args))

    def _drain_queue(self) -> None:
        if self._closing:
            return
        try:
            while True:
                callback, args = self._queue.get_nowait()
                try:
                    callback(*args)
                except Exception:
                    self.logger.exception("处理界面消息失败")
        except queue.Empty:
            pass
        self.root.after(100, self._drain_queue)

    def _run_async(
        self,
        task_name: str,
        work: Callable[[], Any],
        on_success: Callable[[Any], None] | None,
        *,
        show_error: bool = True,
    ) -> None:
        if self._busy:
            return
        self._busy = True
        self._set_actions_enabled(False)
        self._log(f"{task_name}…", "info")

        def runner() -> None:
            try:
                result = work()
            except Exception as exc:  # 交给主线程统一提示
                self.logger.exception("%s失败", task_name)
                self._post(self._task_finished, task_name, None, exc, on_success, show_error)
            else:
                self._post(self._task_finished, task_name, result, None, on_success, show_error)

        threading.Thread(target=runner, name="launcher-worker", daemon=True).start()

    def _task_finished(
        self,
        task_name: str,
        result: Any,
        error: BaseException | None,
        on_success: Callable[[Any], None] | None,
        show_error: bool,
    ) -> None:
        self._busy = False
        self._set_actions_enabled(True)
        if error is not None:
            message = str(error) or error.__class__.__name__
            self._log(f"{task_name}失败：{message}", "error")
            if show_error:
                messagebox.showerror(f"{task_name}失败", message, parent=self.root)
            return
        self._log(f"{task_name}完成。", "muted")
        if on_success is not None:
            try:
                on_success(result)
            except Exception:
                self.logger.exception("完成回调失败")

    def _set_actions_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for button in self._action_buttons:
            try:
                button.configure(state=state)
            except tk.TclError:
                pass

    def _update_order_hint(self) -> None:
        if self.config.launch_order == LAUNCH_ORDER_STEAM_FIRST:
            self.order_hint.configure(text="当前顺序：Steam → 加速器 → 恐鬼症")
        else:
            self.order_hint.configure(text="当前顺序：加速器 → Steam → 恐鬼症")

    # ------------------------------------------------------------------
    # 窗口
    # ------------------------------------------------------------------
    def _set_window_icon(self) -> None:
        icon = resource_path("assets", "app.ico")
        if icon.is_file():
            try:
                self.root.iconbitmap(default=str(icon))
            except tk.TclError:
                pass

    def _enable_dark_title_bar(self) -> None:
        if os.name != "nt":
            return
        try:
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            enabled = ctypes.c_int(1)
            # DWMWA_USE_IMMERSIVE_DARK_MODE：Windows 11 为 20，旧版为 19。
            for attribute in (20, 19):
                result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attribute, ctypes.byref(enabled), ctypes.sizeof(enabled)
                )
                if result == 0:
                    break
        except Exception:
            pass

    def _center_window(self) -> None:
        self.root.update_idletasks()
        width = 960
        height = 720
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2 - 12)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _on_close(self) -> None:
        if self._closing:
            return
        if self._busy:
            messagebox.showinfo(
                "任务进行中",
                "请等待当前启动流程完成后再退出，避免游戏在窗口关闭后才被拉起。",
                parent=self.root,
            )
            return
        self._closing = True
        if self._save_job is not None:
            try:
                self.root.after_cancel(self._save_job)
            except tk.TclError:
                pass
        try:
            self.store.save(self.config)
        except OSError:
            self.logger.exception("退出时保存配置失败")
        self.root.destroy()


def _enable_dpi_awareness() -> None:
    if os.name != "nt":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def run_gui() -> int:
    _enable_dpi_awareness()
    root = tk.Tk()
    LauncherApp(root)
    root.mainloop()
    return 0
