import os
import tempfile
import unittest
from pathlib import Path

from SMS2Clip.runtime import (
    build_service_command,
    build_service_environment,
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
                "SMS2Clip",
                "--service",
                "--config",
                str(Path("C:/work/config.json")),
            ],
        )

    def test_builds_frozen_service_command(self):
        command = build_service_command(
            Path("C:/work/config.json"),
            frozen=True,
            executable=Path("C:/work/SMS2Clip.exe"),
        )
        self.assertEqual(
            command,
            [
                str(Path("C:/work/SMS2Clip.exe")),
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

    def test_service_environment_clears_pyinstaller_runtime_variables(self):
        source = {
            "PATH": "C:/Windows",
            "_MEIPASS2": "C:/Temp/_MEI123",
            "_PYI_APPLICATION_HOME_DIR": "C:/Temp/_MEI123",
            "_PYI_ARCHIVE_FILE": "C:/Apps/SMS2Clip.exe",
            "_PYI_PARENT_PROCESS_LEVEL": "1",
            "_PYI_SPLASH_IPC": "123",
        }

        cleaned = build_service_environment(source)

        self.assertEqual(cleaned["PATH"], "C:/Windows")
        for name in (
            "_MEIPASS2",
            "_PYI_APPLICATION_HOME_DIR",
            "_PYI_ARCHIVE_FILE",
            "_PYI_PARENT_PROCESS_LEVEL",
            "_PYI_SPLASH_IPC",
        ):
            self.assertNotIn(name, cleaned)
            self.assertIn(name, source)


if __name__ == "__main__":
    unittest.main()
