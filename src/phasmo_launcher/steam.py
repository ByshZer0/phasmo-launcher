"""Steam 安装目录、游戏库与《恐鬼症》的检测。"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from .constants import GAME_NAME, STEAM_APP_ID


@dataclass(frozen=True, slots=True)
class SteamEnvironment:
    steam_dir: Path | None = None
    steam_exe: Path | None = None
    library_roots: tuple[Path, ...] = ()
    game_dir: Path | None = None
    game_exe: Path | None = None

    @property
    def steam_available(self) -> bool:
        return bool(self.steam_exe and self.steam_exe.is_file())

    @property
    def game_installed(self) -> bool:
        return bool(self.game_exe and self.game_exe.is_file())

    def summary(self) -> str:
        steam = str(self.steam_dir) if self.steam_available else "未找到"
        game = str(self.game_dir) if self.game_installed else "未安装"
        return f"Steam: {steam}\n游戏: {game}"


def normalize_steam_dir(value: str | Path) -> Path:
    """接受 Steam 根目录、steam.exe 或 steamapps 路径。"""

    text = str(value).strip().strip('"')
    path = Path(os.path.expandvars(text)).expanduser()
    if path.name.lower() == "steam.exe":
        path = path.parent
    elif path.name.lower() == "steamapps":
        path = path.parent
    return path


def candidate_steam_dirs() -> list[Path]:
    """按优先级收集可能的 Steam 根目录。"""

    candidates: list[Path] = []

    for value in (
        _read_registry("HKCU", r"Software\Valve\Steam", "SteamPath"),
        _read_registry("HKLM", r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
        _read_registry("HKLM", r"SOFTWARE\Valve\Steam", "InstallPath"),
    ):
        if value:
            candidates.append(normalize_steam_dir(value))

    for env_name in ("ProgramFiles(x86)", "ProgramFiles"):
        base = os.environ.get(env_name)
        if base:
            candidates.append(Path(base) / "Steam")

    candidates.append(Path(r"C:\Steam"))

    result: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = os.path.normcase(str(path))
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def detect_steam_dir() -> Path | None:
    for candidate in candidate_steam_dirs():
        if (candidate / "steam.exe").is_file():
            return candidate
    return None


def parse_library_folders(text: str) -> list[Path]:
    """解析 libraryfolders.vdf，兼容新旧两种格式。

    新版：``"path" "D:\\\\SteamLibrary"``
    旧版：``"1" "D:\\\\SteamLibrary"``
    """

    paths: list[Path] = []
    seen: set[str] = set()

    def add(raw: str) -> None:
        value = _unescape_vdf(raw).strip()
        if not value:
            return
        key = os.path.normcase(value)
        if key in seen:
            return
        seen.add(key)
        paths.append(Path(value))

    for match in re.finditer(r'"path"\s+"((?:[^"\\]|\\.)*)"', text, re.IGNORECASE):
        add(match.group(1))

    if not paths:
        for match in re.finditer(
            r'^\s*"\d+"\s+"((?:[^"\\]|\\.)*)"\s*$', text, re.MULTILINE
        ):
            add(match.group(1))

    return paths


def parse_app_manifest(text: str) -> dict[str, str]:
    """提取 ACF 中的简单键值对（嵌套段会被展开为键值）。"""

    result: dict[str, str] = {}
    for match in re.finditer(r'"([^"]+)"\s+"([^"]*)"', text):
        result.setdefault(match.group(1), _unescape_vdf(match.group(2)))
    return result


def find_game(library_roots: list[Path] | tuple[Path, ...]) -> tuple[Path | None, Path | None]:
    """在多个 Steam 库中查找《恐鬼症》。

    优先读取 ``appmanifest_739630.acf`` 的 ``installdir``，找不到时回退到
    默认目录名 ``Phasmophobia``。
    """

    manifest_name = f"appmanifest_{STEAM_APP_ID}.acf"
    seen: set[str] = set()

    for root in library_roots:
        steamapps = Path(root) / "steamapps"
        manifest = steamapps / manifest_name
        install_dir: Path | None = None

        if manifest.is_file():
            try:
                data = parse_app_manifest(manifest.read_text(encoding="utf-8-sig", errors="replace"))
            except OSError:
                data = {}
            folder = data.get("installdir", GAME_NAME)
            if folder:
                install_dir = steamapps / "common" / folder

        if install_dir is None:
            fallback = steamapps / "common" / GAME_NAME
            if fallback.is_dir():
                install_dir = fallback

        if install_dir is not None:
            game_dir = install_dir
            exe = game_dir / f"{GAME_NAME}.exe"
            key = os.path.normcase(str(game_dir))
            if key in seen:
                continue
            seen.add(key)
            if exe.is_file():
                return game_dir, exe

    return None, None


def detect_environment(steam_dir: str | Path | None = None) -> SteamEnvironment:
    """检测 Steam 与游戏。

    ``steam_dir`` 为空时自动检测；传入路径时严格使用该路径（方便用户手动指定）。
    """

    if steam_dir is None or str(steam_dir).strip() == "":
        root = detect_steam_dir()
    else:
        root = normalize_steam_dir(steam_dir)
        if not root.is_dir():
            root = None

    if root is None:
        return SteamEnvironment()

    steam_exe = root / "steam.exe"
    if not steam_exe.is_file():
        steam_exe = None

    roots: list[Path] = [root]
    vdf_path = root / "steamapps" / "libraryfolders.vdf"
    if vdf_path.is_file():
        try:
            content = vdf_path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            content = ""
        for library in parse_library_folders(content):
            if library.is_dir():
                roots.append(library)

    unique_roots: list[Path] = []
    seen: set[str] = set()
    for item in roots:
        key = os.path.normcase(str(item))
        if key in seen:
            continue
        seen.add(key)
        unique_roots.append(item)

    game_dir, game_exe = find_game(unique_roots)
    return SteamEnvironment(
        steam_dir=root,
        steam_exe=steam_exe,
        library_roots=tuple(unique_roots),
        game_dir=game_dir,
        game_exe=game_exe,
    )


def _read_registry(hive: str, key: str, value_name: str) -> str | None:
    if os.name != "nt":
        return None
    try:
        import winreg
    except ImportError:
        return None

    root = winreg.HKEY_CURRENT_USER if hive == "HKCU" else winreg.HKEY_LOCAL_MACHINE
    try:
        with winreg.OpenKey(root, key) as handle:
            value, _ = winreg.QueryValueEx(handle, value_name)
    except OSError:
        return None
    return value if isinstance(value, str) else None


def _unescape_vdf(value: str) -> str:
    return value.replace(r"\\", "\\").replace(r"\"", '"')
