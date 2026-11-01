"""应用数据目录与资源路径。"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def app_data_dir() -> Path:
    """返回可写的应用数据目录。

    可用 ``PHASMO_LAUNCHER_HOME`` 覆盖，便于测试与便携部署。
    """

    override = os.environ.get("PHASMO_LAUNCHER_HOME")
    if override:
        return Path(override).expanduser().resolve()

    if os.name == "nt":
        base = os.environ.get("APPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Roaming"
        return root / "PhasmoLauncher"

    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base else Path.home() / ".config"
    return root / "phasmo-launcher"


def config_file() -> Path:
    return app_data_dir() / "config.json"


def log_dir() -> Path:
    return app_data_dir() / "logs"


def log_file() -> Path:
    return log_dir() / "launcher.log"


def ensure_app_dirs() -> None:
    app_data_dir().mkdir(parents=True, exist_ok=True)
    log_dir().mkdir(parents=True, exist_ok=True)


def project_root() -> Path:
    """项目根目录；PyInstaller 打包后指向解包目录。"""

    frozen_base = getattr(sys, "_MEIPASS", None)
    if frozen_base:
        return Path(frozen_base)
    return Path(__file__).resolve().parents[2]


def resource_path(*parts: str) -> Path:
    return project_root().joinpath(*parts)


def open_in_explorer(path: Path | str) -> None:
    """在系统文件管理器中打开目录；失败时静默忽略。"""

    target = Path(path)
    if not target.exists():
        return
    try:
        if os.name == "nt":
            os.startfile(str(target))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            import subprocess

            subprocess.Popen(["open", str(target)])
        else:
            import subprocess

            subprocess.Popen(["xdg-open", str(target)])
    except OSError:
        pass
