"""Windows 平台相关的小工具。

所有函数在没有 Windows API 的环境下都有可用的降级行为，方便测试。
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import webbrowser
from collections.abc import Iterable, Sequence
from pathlib import Path

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_NO_WINDOW = 0x08000000


def is_windows() -> bool:
    return os.name == "nt"


def is_process_running(names: Iterable[str]) -> bool:
    """通过 tasklist 判断进程是否在运行。

    不依赖 psutil，也不会因为某个进程名不存在而抛异常。
    """

    if not is_windows():
        return False

    wanted = {name.lower() for name in names if name}
    if not wanted:
        return False

    try:
        completed = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            encoding="mbcs",
            errors="replace",
            creationflags=CREATE_NO_WINDOW,
            check=False,
        )
    except OSError:
        return False

    if completed.returncode != 0:
        return False

    for line in completed.stdout.splitlines():
        if not line.startswith('"'):
            continue
        image_name = line.split('","', 1)[0].strip('"').strip()
        if image_name.lower() in wanted:
            return True
    return False


def start_detached(command: Sequence[str], cwd: Path | str | None = None) -> subprocess.Popen[bytes]:
    """启动独立进程，启动器退出后子进程继续运行。"""

    if not command:
        raise ValueError("启动命令不能为空")

    kwargs: dict[str, object] = {
        "cwd": str(cwd) if cwd else None,
        "close_fds": True,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if is_windows():
        kwargs["creationflags"] = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

    return subprocess.Popen(list(command), **kwargs)  # type: ignore[arg-type]


def open_target(target: str | Path) -> None:
    """用系统默认方式打开文件、目录或 URL。"""

    value = str(target)
    if is_windows():
        os.startfile(value)  # type: ignore[attr-defined]
        return

    if "://" in value:
        webbrowser.open(value)
    else:
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.Popen([opener, value])


def wait_for_process(
    names: Iterable[str],
    timeout: float,
    *,
    interval: float = 0.5,
    clock=time.monotonic,
    sleeper=time.sleep,
    checker=is_process_running,
) -> bool:
    """轮询等待进程出现，超时返回 False。"""

    deadline = clock() + max(0.0, timeout)
    while True:
        if checker(names):
            return True
        if clock() >= deadline:
            return False
        sleeper(min(interval, max(0.0, deadline - clock())))
