from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from phasmo_launcher.config import AppConfig
from phasmo_launcher.constants import STEAM_GAME_URI
from phasmo_launcher.launcher import LaunchError, LaunchMode, LauncherService
from phasmo_launcher.steam import SteamEnvironment


class FakeRuntime:
    def __init__(self) -> None:
        self.steam_running = False
        self.started: list[list[str]] = []
        self.opened: list[str] = []
        self.slept: list[float] = []

    def start(self, command: list[str], cwd: str | None = None) -> None:
        self.started.append(list(command))
        if Path(command[0]).name.lower() == "steam.exe":
            self.steam_running = True

    def check(self, names: tuple[str, ...]) -> bool:
        return self.steam_running and "steam.exe" in {name.lower() for name in names}

    def open(self, target: str) -> None:
        self.opened.append(target)

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)


class LauncherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.steam_dir = self.root / "Steam"
        self.steam_dir.mkdir()
        self.steam_exe = self.steam_dir / "steam.exe"
        self.steam_exe.write_text("", encoding="utf-8")
        self.game_dir = self.root / "Library" / "steamapps" / "common" / "Phasmophobia"
        self.game_dir.mkdir(parents=True)
        self.game_exe = self.game_dir / "Phasmophobia.exe"
        self.game_exe.write_text("", encoding="utf-8")
        self.accel = self.root / "UU加速器.exe"
        self.accel.write_text("", encoding="utf-8")

        self.env = SteamEnvironment(
            steam_dir=self.steam_dir,
            steam_exe=self.steam_exe,
            library_roots=(self.steam_dir,),
            game_dir=self.game_dir,
            game_exe=self.game_exe,
        )
        self.runtime = FakeRuntime()
        self.service = LauncherService(
            environment_provider=lambda _path=None: self.env,
            process_checker=self.runtime.check,
            starter=self.runtime.start,
            opener=self.runtime.open,
            sleeper=self.runtime.sleep,
            steam_start_timeout=0.2,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def config(self, **overrides) -> AppConfig:
        values = {
            "accelerator_path": str(self.accel),
            "accelerator_wait_seconds": 5,
            "launch_order": "accelerator_first",
        }
        values.update(overrides)
        return AppConfig(**values).normalized()

    def test_all_starts_accelerator_then_steam_then_game(self) -> None:
        result = self.service.run(LaunchMode.ALL, self.config(), environment=self.env)

        self.assertEqual(len(self.runtime.started), 2)
        self.assertEqual(Path(self.runtime.started[0][0]), self.accel)
        self.assertEqual(Path(self.runtime.started[1][0]), self.steam_exe)
        self.assertIn(5, self.runtime.slept)
        self.assertEqual(self.runtime.opened, [STEAM_GAME_URI])
        self.assertTrue(result.accelerator_started)
        self.assertTrue(result.steam_started)
        self.assertTrue(result.game_requested)

    def test_steam_first_order(self) -> None:
        self.service.run(
            LaunchMode.ALL,
            self.config(launch_order="steam_first"),
            environment=self.env,
        )
        self.assertEqual(Path(self.runtime.started[0][0]), self.steam_exe)
        self.assertEqual(Path(self.runtime.started[1][0]), self.accel)

    def test_existing_steam_is_not_started(self) -> None:
        self.runtime.steam_running = True
        result = self.service.run(LaunchMode.ALL, self.config(), environment=self.env)

        self.assertEqual(len(self.runtime.started), 1)
        self.assertFalse(result.steam_started)
        self.assertIn("Steam 已在运行", result.steps)

    def test_game_mode_does_not_require_accelerator(self) -> None:
        result = self.service.run(
            LaunchMode.GAME, self.config(accelerator_path=""), environment=self.env
        )
        self.assertEqual(self.runtime.opened, [STEAM_GAME_URI])
        self.assertFalse(result.accelerator_started)

    def test_protocol_failure_falls_back_to_applaunch(self) -> None:
        self.runtime.steam_running = True

        def broken_opener(target: str) -> None:
            raise OSError("no protocol handler")

        self.service = LauncherService(
            environment_provider=lambda _path=None: self.env,
            process_checker=self.runtime.check,
            starter=self.runtime.start,
            opener=broken_opener,
            sleeper=self.runtime.sleep,
            steam_start_timeout=0.2,
        )
        result = self.service.run(LaunchMode.GAME, self.config(), environment=self.env)

        self.assertTrue(result.game_requested)
        self.assertEqual(
            self.runtime.started[-1],
            [str(self.steam_exe), "-applaunch", "739630"],
        )

    def test_steam_mode_does_not_require_game_or_accelerator(self) -> None:
        env = SteamEnvironment(
            steam_dir=self.steam_dir,
            steam_exe=self.steam_exe,
            library_roots=(self.steam_dir,),
        )
        result = self.service.run(
            LaunchMode.STEAM, self.config(accelerator_path=""), environment=env
        )
        self.assertTrue(result.steam_started)
        self.assertFalse(result.game_requested)

    def test_accelerator_mode_does_not_require_steam(self) -> None:
        result = self.service.run(
            LaunchMode.ACCELERATOR,
            self.config(),
            environment=SteamEnvironment(),
        )
        self.assertTrue(result.accelerator_started)
        self.assertFalse(result.steam_started)

    def test_missing_accelerator_fails_before_starting_anything(self) -> None:
        with self.assertRaises(LaunchError):
            self.service.run(
                LaunchMode.ALL, self.config(accelerator_path=""), environment=self.env
            )
        self.assertEqual(self.runtime.started, [])

    def test_missing_game_fails(self) -> None:
        env = SteamEnvironment(
            steam_dir=self.steam_dir,
            steam_exe=self.steam_exe,
            library_roots=(self.steam_dir,),
        )
        with self.assertRaises(LaunchError):
            self.service.run(LaunchMode.GAME, self.config(), environment=env)
        self.assertEqual(self.runtime.started, [])

    def test_steam_start_timeout(self) -> None:
        self.runtime.check = lambda names: False  # type: ignore[assignment]
        self.service = LauncherService(
            environment_provider=lambda _path=None: self.env,
            process_checker=self.runtime.check,
            starter=self.runtime.start,
            opener=self.runtime.open,
            sleeper=self.runtime.sleep,
            steam_start_timeout=0,
        )
        with self.assertRaises(LaunchError):
            self.service.run(LaunchMode.STEAM, self.config(), environment=self.env)

    def test_progress_messages(self) -> None:
        messages: list[str] = []
        self.service.run(
            LaunchMode.ALL, self.config(), environment=self.env, progress=messages.append
        )
        self.assertTrue(any("加速器" in message for message in messages))
        self.assertTrue(any("Steam" in message for message in messages))
        self.assertTrue(any("恐鬼症" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
