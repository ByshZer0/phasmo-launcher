"""配置模型与持久化。

配置默认保存在 ``%APPDATA%\\PhasmoLauncher\\config.json``。
写入采用「临时文件 + 原子替换」，避免程序被强制结束时损坏配置。
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .constants import (
    DEFAULT_ACCELERATOR_WAIT,
    LAUNCH_ORDER_ACCELERATOR_FIRST,
    LAUNCH_ORDERS,
    MAX_ACCELERATOR_WAIT,
)
from .paths import config_file

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AppConfig:
    """用户配置。空路径表示自动检测。"""

    steam_path: str = ""
    accelerator_path: str = ""
    accelerator_args: str = ""
    accelerator_wait_seconds: int = DEFAULT_ACCELERATOR_WAIT
    launch_order: str = LAUNCH_ORDER_ACCELERATOR_FIRST
    close_after_launch: bool = False

    def normalized(self) -> "AppConfig":
        """返回清洗后的副本，不修改原对象。"""

        wait = _safe_int(self.accelerator_wait_seconds, DEFAULT_ACCELERATOR_WAIT)
        wait = max(0, min(MAX_ACCELERATOR_WAIT, wait))
        order = self.launch_order if self.launch_order in LAUNCH_ORDERS else LAUNCH_ORDER_ACCELERATOR_FIRST
        return AppConfig(
            steam_path=str(self.steam_path or "").strip(),
            accelerator_path=str(self.accelerator_path or "").strip(),
            accelerator_args=str(self.accelerator_args or "").strip(),
            accelerator_wait_seconds=wait,
            launch_order=order,
            close_after_launch=bool(self.close_after_launch),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self.normalized())

    @classmethod
    def from_dict(cls, raw: Any) -> "AppConfig":
        if not isinstance(raw, dict):
            return cls()
        return cls(
            steam_path=_as_str(raw.get("steam_path")),
            accelerator_path=_as_str(raw.get("accelerator_path")),
            accelerator_args=_as_str(raw.get("accelerator_args")),
            accelerator_wait_seconds=_safe_int(
                raw.get("accelerator_wait_seconds"), DEFAULT_ACCELERATOR_WAIT
            ),
            launch_order=_as_str(raw.get("launch_order")) or LAUNCH_ORDER_ACCELERATOR_FIRST,
            close_after_launch=_as_bool(raw.get("close_after_launch"), False),
        ).normalized()


class ConfigStore:
    """读写 JSON 配置，遇到损坏文件时回退到默认值。"""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else config_file()

    def load(self) -> AppConfig:
        if not self.path.exists():
            return AppConfig()
        try:
            text = self.path.read_text(encoding="utf-8-sig")
            raw = json.loads(text)
        except (OSError, ValueError) as exc:
            logger.warning("读取配置失败，使用默认配置：%s", exc)
            return AppConfig()

        if not isinstance(raw, dict):
            logger.warning("配置文件根节点不是对象，使用默认配置：%s", self.path)
            return AppConfig()
        return AppConfig.from_dict(raw)

    def save(self, config: AppConfig) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(config.to_dict(), ensure_ascii=False, indent=2) + "\n"

        fd, temp_name = tempfile.mkstemp(
            prefix=f".{self.path.stem}-", suffix=".tmp", dir=str(self.path.parent)
        )
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self.path)
        except Exception:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise
        logger.info("配置已保存：%s", self.path)
        return self.path


def _as_str(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
