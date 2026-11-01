"""启动编排：加速器 → Steam → 恐鬼症。"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from . import accelerator
from .accelerator import AcceleratorSpec
from .config import AppConfig
from .constants import (
    DEFAULT_STEAM_START_TIMEOUT,
    GAME_NAME_CN,
    LAUNCH_ORDER_STEAM_FIRST,
    MODE_ACCELERATOR,
    MODE_ALL,
    MODE_GAME,
    MODE_STEAM,
    STEAM_APP_ID,
    STEAM_GAME_URI,
)
from .steam import SteamEnvironment, detect_environment
from .windows import is_process_running, open_target, start_detached, wait_for_process

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str], None]


class LaunchMode(str, Enum):
    ALL = MODE_ALL
    GAME = MODE_GAME
    STEAM = MODE_STEAM
    ACCELERATOR = MODE_ACCELERATOR


class LaunchError(RuntimeError):
    """预检失败或启动超时。"""


@dataclass(slots=True)
class LaunchResult:
    mode: LaunchMode
    steps: list[str] = field(default_factory=list)
    accelerator_started: bool = False
    steam_started: bool = False
    game_requested: bool = False


class LauncherService:
    """可测试的启动流程。

    外部依赖均通过构造参数注入，默认使用 Windows 实现。
    """

    def __init__(
        self,
        *,
        environment_provider: Callable[..., SteamEnvironment] = detect_environment,
        process_checker: Callable[[tuple[str, ...]], bool] = is_process_running,
        starter: Callable[..., object] = start_detached,
        opener: Callable[[str], None] = open_target,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        steam_start_timeout: float = DEFAULT_STEAM_START_TIMEOUT,
    ) -> None:
        self._environment_provider = environment_provider
        self._process_checker = process_checker
        self._starter = starter
        self._opener = opener
        self._clock = clock
        self._sleep = sleeper
        self.steam_start_timeout = steam_start_timeout

    def detect(self, config: AppConfig) -> SteamEnvironment:
        return self._environment_provider(config.steam_path or None)

    def run(
        self,
        mode: LaunchMode | str,
        config: AppConfig,
        *,
        environment: SteamEnvironment | None = None,
        progress: ProgressCallback | None = None,
    ) -> LaunchResult:
        mode = LaunchMode(mode)
        config = config.normalized()
        env = environment if environment is not None else self.detect(config)
        result = LaunchResult(mode=mode)
        emit = _make_emitter(progress)

        self._preflight(mode, config, env)

        if mode is LaunchMode.ALL:
            if config.launch_order == LAUNCH_ORDER_STEAM_FIRST:
                self._ensure_steam(env, result, emit)
                self._start_accelerator(config, result, emit)
            else:
                self._start_accelerator(config, result, emit)
                self._ensure_steam(env, result, emit)
            self._request_game(env, result, emit)
        elif mode is LaunchMode.GAME:
            self._ensure_steam(env, result, emit)
            self._request_game(env, result, emit)
        elif mode is LaunchMode.STEAM:
            self._ensure_steam(env, result, emit)
        elif mode is LaunchMode.ACCELERATOR:
            self._start_accelerator(config, result, emit)

        return result

    # ------------------------------------------------------------------
    # 预检
    # ------------------------------------------------------------------
    def _preflight(self, mode: LaunchMode, config: AppConfig, env: SteamEnvironment) -> None:
        if mode in (LaunchMode.ALL, LaunchMode.STEAM, LaunchMode.GAME):
            if not env.steam_available:
                raise LaunchError(
                    "未找到 Steam。请安装 Steam，或在「启动设置」中手动选择 Steam 目录。"
                )
        if mode in (LaunchMode.ALL, LaunchMode.GAME) and not env.game_installed:
            raise LaunchError(
                f"未检测到{GAME_NAME_CN}。请先在 Steam 中安装 {GAME_NAME_CN}"
                "（AppID 739630），并确认游戏文件完整。"
            )
        if mode in (LaunchMode.ALL, LaunchMode.ACCELERATOR):
            spec = self._spec(config)
            error = accelerator.validate_spec(spec)
            if error:
                hint = (
                    "一键启动需要先在「启动设置」中选择加速器程序。"
                    if mode is LaunchMode.ALL
                    else "请先检查「启动设置」中的加速器程序。"
                )
                raise LaunchError(f"{error}\n{hint}")

    # ------------------------------------------------------------------
    # 各步骤
    # ------------------------------------------------------------------
    def _start_accelerator(
        self, config: AppConfig, result: LaunchResult, emit: ProgressCallback
    ) -> None:
        spec = self._spec(config)
        emit(f"正在启动加速器：{spec.name}")
        try:
            accelerator.launch(spec, starter=self._starter, opener=self._opener)
        except accelerator.AcceleratorError as exc:
            raise LaunchError(str(exc)) from exc
        except OSError as exc:
            if getattr(exc, "winerror", None) == 740:
                raise LaunchError(
                    "加速器需要管理员权限。请关闭启动器，右键选择"
                    "「以管理员身份运行」后重试。"
                ) from exc
            raise LaunchError(f"启动加速器失败：{exc}") from exc
        result.accelerator_started = True
        result.steps.append(f"已启动加速器：{spec.name}")

        wait_seconds = max(0, config.accelerator_wait_seconds)
        if wait_seconds:
            emit(f"等待 {wait_seconds} 秒，让加速器完成初始化…")
            self._sleep(wait_seconds)
        emit("加速器启动阶段完成。")

    def _ensure_steam(
        self, env: SteamEnvironment, result: LaunchResult, emit: ProgressCallback
    ) -> None:
        if self._process_checker(("steam.exe",)):
            emit("Steam 已在运行，跳过启动。")
            result.steps.append("Steam 已在运行")
            return

        if not env.steam_exe:
            raise LaunchError("Steam 可执行文件不存在，请重新选择 Steam 目录。")

        emit("正在启动 Steam…")
        try:
            self._starter([str(env.steam_exe)], cwd=str(env.steam_dir) if env.steam_dir else None)
        except OSError as exc:
            raise LaunchError(f"启动 Steam 失败：{exc}") from exc

        emit(f"等待 Steam 启动（最多 {int(self.steam_start_timeout)} 秒）…")
        started = wait_for_process(
            ("steam.exe",),
            self.steam_start_timeout,
            clock=self._clock,
            sleeper=self._sleep,
            checker=lambda names: self._process_checker(tuple(names)),
        )
        if not started:
            raise LaunchError(
                "Steam 启动超时。请手动打开 Steam 并登录后，再使用本启动器。"
            )
        result.steam_started = True
        result.steps.append("已启动 Steam")

    def _request_game(
        self, env: SteamEnvironment, result: LaunchResult, emit: ProgressCallback
    ) -> None:
        emit(f"正在通过 Steam 启动{GAME_NAME_CN}…")
        try:
            self._opener(STEAM_GAME_URI)
        except OSError as exc:
            # 极少数系统没有注册 steam:// 协议，退回 Steam 自带的 -applaunch。
            emit(f"steam:// 协议唤起失败，尝试 Steam -applaunch：{exc}")
            if not env.steam_exe:
                raise LaunchError(
                    f"无法唤起 Steam 游戏协议：{exc}\n"
                    "请确认 Steam 已正确安装并关联 steam:// 协议。"
                ) from exc
            try:
                self._starter(
                    [str(env.steam_exe), "-applaunch", str(STEAM_APP_ID)],
                    cwd=str(env.steam_dir) if env.steam_dir else None,
                )
            except OSError as fallback_exc:
                raise LaunchError(
                    f"无法启动{GAME_NAME_CN}：{fallback_exc}\n"
                    "请确认 Steam 已正确安装并关联 steam:// 协议。"
                ) from fallback_exc
        result.game_requested = True
        result.steps.append(f"已请求启动{GAME_NAME_CN}")

    @staticmethod
    def _spec(config: AppConfig) -> AcceleratorSpec:
        return AcceleratorSpec(
            path=config.accelerator_path,
            args=config.accelerator_args,
            wait_seconds=config.accelerator_wait_seconds,
        )


def _make_emitter(progress: ProgressCallback | None) -> ProgressCallback:
    def emit(message: str) -> None:
        logger.info(message)
        if progress is not None:
            progress(message)

    return emit
