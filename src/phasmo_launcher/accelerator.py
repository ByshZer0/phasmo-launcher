"""第三方加速器的配置校验与启动。

本模块只负责「拉起用户已安装的加速器」，不提供也不代理任何加速线路。
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .constants import DEFAULT_ACCELERATOR_WAIT
from .windows import open_target, start_detached

logger = logging.getLogger(__name__)

_PROTOCOL_RE = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]*)://")
_ALLOWED_SUFFIXES = {".exe", ".com", ".lnk"}


class AcceleratorError(RuntimeError):
    """加速器配置或启动失败。"""


@dataclass(frozen=True, slots=True)
class AcceleratorSpec:
    path: str = ""
    args: str = ""
    wait_seconds: int = DEFAULT_ACCELERATOR_WAIT

    @property
    def configured(self) -> bool:
        return bool(self.path.strip())

    @property
    def name(self) -> str:
        protocol = protocol_scheme(self.path)
        if protocol:
            return f"{protocol} 协议"
        name = Path(self.path).name if self.path else ""
        return name or "未配置"


def protocol_scheme(value: str) -> str | None:
    match = _PROTOCOL_RE.match(value.strip())
    if not match:
        return None
    scheme = match.group(1).lower()
    return None if scheme == "file" else scheme


def _resolve_path(raw: str) -> Path:
    cleaned = raw.strip().strip('"')
    return Path(os.path.expandvars(os.path.expanduser(cleaned)))


def split_arguments(raw: str) -> list[str]:
    """按 Windows 习惯拆分参数：支持双引号，保留反斜杠路径。

    例：``--profile "Phasmophobia" --mode fast`` ->
    ``["--profile", "Phasmophobia", "--mode", "fast"]``
    """

    if not raw or not raw.strip():
        return []

    result: list[str] = []
    buffer: list[str] = []
    in_quotes = False
    index = 0

    while index < len(raw):
        char = raw[index]
        if char == '"':
            in_quotes = not in_quotes
        elif char == "\\" and index + 1 < len(raw) and raw[index + 1] == '"':
            buffer.append('"')
            index += 1
        elif char.isspace() and not in_quotes:
            if buffer:
                result.append("".join(buffer))
                buffer.clear()
        else:
            buffer.append(char)
        index += 1

    if buffer:
        result.append("".join(buffer))
    return result


def validate_spec(spec: AcceleratorSpec) -> str | None:
    """返回错误说明；配置有效时返回 ``None``。"""

    raw_path = spec.path.strip()
    if not raw_path:
        return "尚未选择加速器程序。"

    if protocol_scheme(raw_path):
        return None

    path = _resolve_path(raw_path)
    if not path.exists():
        return f"加速器路径不存在：{path}"
    if not path.is_file():
        return f"加速器路径不是文件：{path}"
    if path.suffix.lower() not in _ALLOWED_SUFFIXES:
        return "请选择 .exe、.com 或 .lnk 文件。"
    if path.suffix.lower() == ".lnk" and split_arguments(spec.args):
        return "快捷方式不支持附加参数，请直接选择加速器的 exe。"
    return None


def launch(
    spec: AcceleratorSpec,
    *,
    starter: Callable[..., object] = start_detached,
    opener: Callable[[str | Path], None] = open_target,
) -> None:
    """拉起加速器（不等待加速完成）。"""

    error = validate_spec(spec)
    if error:
        raise AcceleratorError(error)

    raw_path = spec.path.strip()
    if protocol_scheme(raw_path):
        logger.info("通过协议启动加速器：%s", raw_path)
        opener(raw_path)
        return

    path = _resolve_path(raw_path)
    if path.suffix.lower() == ".lnk":
        logger.info("通过快捷方式启动加速器：%s", path)
        opener(str(path))
        return

    arguments = split_arguments(spec.args)
    command = [str(path), *arguments]
    logger.info("启动加速器：%s", command)
    starter(command, cwd=str(path.parent))
