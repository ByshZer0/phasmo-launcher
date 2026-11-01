#!/usr/bin/env python3
"""源码运行入口。

直接运行 ``python main.py`` 即可，无需安装依赖。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from phasmo_launcher.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
