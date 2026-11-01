"""命令行入口：GUI、环境诊断与无界面启动。"""

from __future__ import annotations

import argparse
import sys

from . import accelerator
from .accelerator import AcceleratorSpec
from .config import ConfigStore
from .constants import (
    APP_NAME,
    GAME_NAME_CN,
    LAUNCH_MODES,
    VERSION,
)
from .launcher import LaunchError, LaunchMode, LauncherService
from .logging_setup import setup_logging
from .steam import detect_environment


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="phasmo-launcher",
        description=f"{APP_NAME}：一键拉起加速器、Steam 与《恐鬼症》。",
    )
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {VERSION}")
    parser.add_argument(
        "--check",
        action="store_true",
        help="只检测 Steam、游戏和加速器配置，不启动任何程序。",
    )
    parser.add_argument(
        "--launch",
        choices=LAUNCH_MODES,
        metavar="MODE",
        help="无界面启动：all / game / steam / accelerator。",
    )
    parser.add_argument("--debug", action="store_true", help="输出调试日志。")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging(debug=args.debug)

    if args.check:
        return _check()
    if args.launch:
        return _launch(LaunchMode(args.launch))
    return _gui()


def _check() -> int:
    store = ConfigStore()
    config = store.load()
    env = detect_environment(config.steam_path or None)
    spec = AcceleratorSpec(
        path=config.accelerator_path,
        args=config.accelerator_args,
        wait_seconds=config.accelerator_wait_seconds,
    )
    accel_error = accelerator.validate_spec(spec)

    print(f"{APP_NAME} v{VERSION}")
    print(f"配置文件 : {store.path}")
    print(f"Steam    : {'OK  ' + str(env.steam_dir) if env.steam_available else '未找到'}")
    print(f"游戏库   : {', '.join(str(p) for p in env.library_roots) or '未找到'}")
    print(
        "恐鬼症   : "
        + (f"OK  {env.game_exe}" if env.game_installed else f"未安装（AppID 739630）")
    )
    print(
        "加速器   : "
        + ("OK  " + spec.name if spec.configured and not accel_error else (accel_error or "未配置"))
    )

    ok = env.steam_available and env.game_installed
    if not ok:
        print("\n提示：请确认 Steam 已安装、游戏已下载，或手动指定 Steam 目录。")
    return 0 if ok else 1


def _launch(mode: LaunchMode) -> int:
    config = ConfigStore().load()
    service = LauncherService()
    print(f"{APP_NAME}：开始执行 {mode.value} 流程…")
    try:
        result = service.run(mode, config, progress=lambda message: print(f"  · {message}"))
    except LaunchError as exc:
        print(f"\n启动失败：{exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"\n系统错误：{exc}", file=sys.stderr)
        return 2

    print("\n完成：")
    for step in result.steps:
        print(f"  ✓ {step}")
    if result.game_requested:
        print(f"  ✓ 已请求 Steam 启动{GAME_NAME_CN}")
    return 0


def _gui() -> int:
    from .app import run_gui

    return run_gui()


def _main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(_main())
