from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from phasmo_launcher.steam import (
    detect_environment,
    find_game,
    normalize_steam_dir,
    parse_app_manifest,
    parse_library_folders,
)


class SteamParsingTests(unittest.TestCase):
    def test_parse_library_folders_new_format(self) -> None:
        text = r'''
"libraryfolders"
{
    "0"
    {
        "path"        "C:\\Program Files (x86)\\Steam"
        "label"       ""
    }
    "1"
    {
        "path"        "D:\\SteamLibrary"
        "apps"        { "739630" "12345" }
    }
}
'''
        paths = parse_library_folders(text)
        self.assertEqual(
            [str(p) for p in paths],
            [r"C:\Program Files (x86)\Steam", r"D:\SteamLibrary"],
        )

    def test_parse_library_folders_old_format(self) -> None:
        text = r'''
"LibraryFolders"
{
    "TimeNextStatsReport" "123"
    "1" "D:\\Games\\Steam"
    "2" "E:\\SteamLibrary"
}
'''
        self.assertEqual(
            [str(p) for p in parse_library_folders(text)],
            [r"D:\Games\Steam", r"E:\SteamLibrary"],
        )

    def test_parse_app_manifest(self) -> None:
        text = r'''
"AppState"
{
    "appid"       "739630"
    "name"        "Phasmophobia"
    "installdir"  "Phasmophobia"
}
'''
        data = parse_app_manifest(text)
        self.assertEqual(data["appid"], "739630")
        self.assertEqual(data["installdir"], "Phasmophobia")

    def test_normalize_steam_dir_accepts_exe_and_steamapps(self) -> None:
        self.assertEqual(str(normalize_steam_dir(r"D:\Steam\steam.exe")), r"D:\Steam")
        self.assertEqual(str(normalize_steam_dir(r"D:\Steam\steamapps")), r"D:\Steam")


class SteamDetectionTests(unittest.TestCase):
    def _make_env(self, tmp: Path) -> tuple[Path, Path, Path]:
        steam = tmp / "Steam"
        (steam / "steamapps").mkdir(parents=True)
        (steam / "steam.exe").write_text("", encoding="utf-8")

        library = tmp / "Library"
        game_dir = library / "steamapps" / "common" / "Phasmophobia"
        game_dir.mkdir(parents=True)
        game_exe = game_dir / "Phasmophobia.exe"
        game_exe.write_text("", encoding="utf-8")
        (library / "steamapps" / "appmanifest_739630.acf").write_text(
            '"AppState"\n{\n "appid" "739630"\n "installdir" "Phasmophobia"\n}\n',
            encoding="utf-8",
        )
        vdf = steam / "steamapps" / "libraryfolders.vdf"
        escaped = str(library).replace("\\", "\\\\")
        vdf.write_text(
            f'"libraryfolders"\n{{\n "1"\n {{\n  "path" "{escaped}"\n }}\n}}\n',
            encoding="utf-8",
        )
        return steam, library, game_exe

    def test_detect_game_in_secondary_library(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            steam, library, game_exe = self._make_env(Path(tmp))
            env = detect_environment(steam)
            self.assertTrue(env.steam_available)
            self.assertTrue(env.game_installed)
            self.assertEqual(env.game_exe, game_exe)
            self.assertIn(library, env.library_roots)

    def test_detect_without_game(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            steam = Path(tmp) / "Steam"
            (steam / "steamapps").mkdir(parents=True)
            (steam / "steam.exe").write_text("", encoding="utf-8")
            env = detect_environment(steam)
            self.assertTrue(env.steam_available)
            self.assertFalse(env.game_installed)
            self.assertIsNone(env.game_dir)

    def test_detect_invalid_manual_path(self) -> None:
        env = detect_environment(r"Z:\definitely-not-a-steam-folder")
        self.assertFalse(env.steam_available)

    def test_find_game_falls_back_to_default_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            library = Path(tmp)
            game_dir = library / "steamapps" / "common" / "Phasmophobia"
            game_dir.mkdir(parents=True)
            exe = game_dir / "Phasmophobia.exe"
            exe.write_text("", encoding="utf-8")
            found_dir, found_exe = find_game([library])

        self.assertEqual(found_dir, game_dir)
        self.assertEqual(found_exe, exe)


if __name__ == "__main__":
    unittest.main()
