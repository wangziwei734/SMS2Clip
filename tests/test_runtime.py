import os
import tempfile
import unittest
from pathlib import Path

from ntfy_clipboard.runtime import (
    build_service_command,
    process_is_running,
    read_pid,
)


class RuntimeTests(unittest.TestCase):
    def test_builds_source_service_command(self):
        command = build_service_command(
            Path("C:/work/config.json"),
            frozen=False,
            executable=Path("C:/Python/pythonw.exe"),
        )
        self.assertEqual(
            command,
            [
                str(Path("C:/Python/pythonw.exe")),
                "-m",
                "ntfy_clipboard",
                "--service",
                "--config",
                str(Path("C:/work/config.json")),
            ],
        )

    def test_builds_frozen_service_command(self):
        command = build_service_command(
            Path("C:/work/config.json"),
            frozen=True,
            executable=Path("C:/work/NtfyClipboard.exe"),
        )
        self.assertEqual(
            command,
            [
                str(Path("C:/work/NtfyClipboard.exe")),
                "--service",
                "--config",
                str(Path("C:/work/config.json")),
            ],
        )

    def test_read_pid_returns_none_for_missing_or_invalid_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pid"
            self.assertIsNone(read_pid(path))
            path.write_text("not-a-number", encoding="ascii")
            self.assertIsNone(read_pid(path))
            path.write_text("1234", encoding="ascii")
            self.assertEqual(read_pid(path), 1234)

    def test_process_is_running_checks_real_process(self):
        self.assertTrue(process_is_running(os.getpid()))
        self.assertFalse(process_is_running(99_999_999))


if __name__ == "__main__":
    unittest.main()
