from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from phasmo_launcher import accelerator
from phasmo_launcher.accelerator import AcceleratorError, AcceleratorSpec, split_arguments


class ArgumentTests(unittest.TestCase):
    def test_quotes_and_backslashes(self) -> None:
        raw = r'--profile "C:\Program Files\Phasmo" --mode fast'
        self.assertEqual(
            split_arguments(raw),
            ["--profile", r"C:\Program Files\Phasmo", "--mode", "fast"],
        )

    def test_empty(self) -> None:
        self.assertEqual(split_arguments(""), [])
        self.assertEqual(split_arguments("   "), [])

    def test_escaped_quote(self) -> None:
        self.assertEqual(split_arguments(r'--name "a\"b"'), ["--name", 'a"b'])


class ValidationTests(unittest.TestCase):
    def test_empty_config(self) -> None:
        self.assertIn("尚未选择", accelerator.validate_spec(AcceleratorSpec()) or "")

    def test_missing_file(self) -> None:
        error = accelerator.validate_spec(AcceleratorSpec(path=r"Z:\nope\uu.exe"))
        self.assertIn("不存在", error or "")

    def test_rejects_script_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "launch.bat"
            script.write_text("echo hi", encoding="utf-8")
            error = accelerator.validate_spec(AcceleratorSpec(path=str(script)))
        self.assertIn(".exe", error or "")

    def test_accepts_protocol(self) -> None:
        spec = AcceleratorSpec(path="uu://launch")
        self.assertIsNone(accelerator.validate_spec(spec))
        self.assertEqual(spec.name, "uu 协议")

    def test_lnk_with_args_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lnk = Path(tmp) / "加速器.lnk"
            lnk.write_text("", encoding="utf-8")
            error = accelerator.validate_spec(AcceleratorSpec(path=str(lnk), args="--fast"))
        self.assertIn("快捷方式", error or "")


class LaunchTests(unittest.TestCase):
    def test_exe_launch_forwards_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "UU加速器.exe"
            exe.write_text("", encoding="utf-8")
            calls: list[tuple[list[str], str | None]] = []

            def starter(command: list[str], cwd: str | None = None) -> None:
                calls.append((command, cwd))

            accelerator.launch(
                AcceleratorSpec(path=str(exe), args='--profile "恐鬼症"'),
                starter=starter,
                opener=lambda _: None,
            )

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], [str(exe), "--profile", "恐鬼症"])
        self.assertEqual(calls[0][1], str(exe.parent))

    def test_protocol_uses_opener(self) -> None:
        opened: list[str] = []
        accelerator.launch(
            AcceleratorSpec(path="uu://launch"),
            starter=lambda *args, **kwargs: None,
            opener=lambda target: opened.append(str(target)),
        )
        self.assertEqual(opened, ["uu://launch"])

    def test_invalid_launch_raises(self) -> None:
        with self.assertRaises(AcceleratorError):
            accelerator.launch(AcceleratorSpec(path=r"Z:\nope\uu.exe"))


if __name__ == "__main__":
    unittest.main()
