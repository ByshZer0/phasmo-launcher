"""日志配置：控制台（如果存在）+ 滚动文件。"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from .paths import ensure_app_dirs, log_file


def setup_logging(debug: bool = False) -> logging.Logger:
    logger = logging.getLogger("phasmo_launcher")
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        ensure_app_dirs()
        file_handler = RotatingFileHandler(
            log_file(), maxBytes=1_500_000, backupCount=3, encoding="utf-8"
        )
    except OSError:
        # 数据目录不可写时仍允许界面启动，只是没有文件日志。
        file_handler = None
    else:
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if sys.stderr is not None:
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(formatter)
        logger.addHandler(console)

    if debug:
        logger.debug("调试日志已启用：%s", log_file())
    return logger
