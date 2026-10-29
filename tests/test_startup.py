import subprocess
import unittest
from pathlib import Path

from ntfy_clipboard.startup import build_startup_command


class StartupTests(unittest.TestCase):
    def test_builds_frozen_startup_command(self):
        executable = Path("C:/Apps/NtfyClipboard.exe")
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
                    "ntfy_clipboard.gui",
                    "--minimized",
                    "--config",
                    str(config_path),
                ]
            ),
        )


if __name__ == "__main__":
    unittest.main()
