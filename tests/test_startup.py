import subprocess
import unittest
from pathlib import Path

from SMS2Clip.startup import build_startup_command, startup_mode_from_command


class StartupTests(unittest.TestCase):
    def test_builds_frozen_startup_command(self):
        executable = Path("C:/Apps/SMS2Clip.exe")
        config_path = Path("C:/Apps/config.json")
        command = build_startup_command(
            frozen=True,
            executable=executable,
            config_path=config_path,
        )
        self.assertEqual(
            command,
            subprocess.list2cmdline(
                [str(executable), "--minimized", "--config", str(config_path)]
            ),
        )

    def test_builds_source_startup_command(self):
        executable = Path("C:/Python/pythonw.exe")
        config_path = Path("C:/Apps/config.json")
        command = build_startup_command(
            frozen=False,
            executable=executable,
            config_path=config_path,
        )
        self.assertEqual(
            command,
            subprocess.list2cmdline(
                [
                    str(executable),
                    "-m",
                    "SMS2Clip.gui",
                    "--minimized",
                    "--config",
                    str(config_path),
                ]
            ),
        )

    def test_builds_frozen_service_startup_command(self):
        executable = Path("C:/Apps/SMS2Clip.exe")
        config_path = Path("C:/Apps/config.json")
        command = build_startup_command(
            frozen=True,
            executable=executable,
            config_path=config_path,
            mode="service",
        )
        self.assertEqual(
            command,
            subprocess.list2cmdline(
                [str(executable), "--service", "--config", str(config_path)]
            ),
        )

    def test_builds_source_service_startup_command(self):
        executable = Path("C:/Python/pythonw.exe")
        config_path = Path("C:/Apps/config.json")
        command = build_startup_command(
            frozen=False,
            executable=executable,
            config_path=config_path,
            mode="service",
        )
        self.assertEqual(
            command,
            subprocess.list2cmdline(
                [
                    str(executable),
                    "-m",
                    "SMS2Clip",
                    "--service",
                    "--config",
                    str(config_path),
                ]
            ),
        )

    def test_detects_startup_mode_from_saved_command(self):
        self.assertEqual(startup_mode_from_command(""), "manual")
        self.assertEqual(
            startup_mode_from_command('"C:/Apps/SMS2Clip.exe" --minimized'),
            "manager",
        )
        self.assertEqual(
            startup_mode_from_command('"C:/Apps/SMS2Clip.exe" --service'),
            "service",
        )


if __name__ == "__main__":
    unittest.main()
