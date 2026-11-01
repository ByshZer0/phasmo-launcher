from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from phasmo_launcher.config import AppConfig, ConfigStore
from phasmo_launcher.constants import DEFAULT_ACCELERATOR_WAIT, MAX_ACCELERATOR_WAIT


class ConfigTests(unittest.TestCase):
    def test_round_trip_preserves_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ConfigStore(Path(tmp) / "config.json")
            original = AppConfig(
                steam_path=r"D:\Steam",
                accelerator_path=r"C:\Tools\加速器.exe",
                accelerator_args='--profile "Phasmophobia"',
                accelerator_wait_seconds=18,
                launch_order="steam_first",
                close_after_launch=True,
            )
            store.save(original)
            loaded = store.load()

        self.assertEqual(loaded, original)
        self.assertEqual(loaded.accelerator_args, '--profile "Phasmophobia"')

    def test_from_dict_ignores_unknown_and_clamps(self) -> None:
        config = AppConfig.from_dict(
            {
                "steam_path": "  E:\\Steam  ",
                "accelerator_wait_seconds": 9999,
                "launch_order": "invalid",
                "close_after_launch": "yes",
                "unknown": "ignored",
            }
        )
        self.assertEqual(config.steam_path, "E:\\Steam")
        self.assertEqual(config.accelerator_wait_seconds, MAX_ACCELERATOR_WAIT)
        self.assertEqual(config.launch_order, "accelerator_first")
        self.assertTrue(config.close_after_launch)

    def test_negative_wait_is_clamped(self) -> None:
        config = AppConfig(accelerator_wait_seconds=-8).normalized()
        self.assertEqual(config.accelerator_wait_seconds, 0)

    def test_bad_wait_uses_default(self) -> None:
        config = AppConfig.from_dict({"accelerator_wait_seconds": "abc"})
        self.assertEqual(config.accelerator_wait_seconds, DEFAULT_ACCELERATOR_WAIT)

    def test_missing_file_returns_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            loaded = ConfigStore(Path(tmp) / "none.json").load()
        self.assertEqual(loaded, AppConfig())

    def test_corrupt_json_returns_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text("{not json", encoding="utf-8")
            loaded = ConfigStore(path).load()
        self.assertEqual(loaded, AppConfig())

    def test_save_is_atomic_and_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            store = ConfigStore(path)
            store.save(AppConfig(accelerator_path=r"C:\加速器\uu.exe"))
            raw = json.loads(path.read_text(encoding="utf-8"))
            leftovers = list(Path(tmp).glob("*.tmp"))

        self.assertEqual(raw["accelerator_path"], r"C:\加速器\uu.exe")
        self.assertEqual(leftovers, [])

    def test_default_path_honours_environment_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"PHASMO_LAUNCHER_HOME": tmp}):
                self.assertEqual(ConfigStore().path, Path(tmp) / "config.json")


if __name__ == "__main__":
    unittest.main()
