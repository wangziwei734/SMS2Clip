"""Windows login-startup registration using the HKCU Run key."""

from __future__ import annotations

import subprocess
from pathlib import Path

VALUE_NAME = "NtfyClipboard"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def build_startup_command(
    frozen: bool,
    executable: Path,
    config_path: Path,
) -> str:
    if frozen:
        arguments = [str(executable), "--minimized", "--config", str(config_path)]
    else:
        arguments = [
            str(executable),
            "-m",
            "ntfy_clipboard.gui",
            "--minimized",
            "--config",
            str(config_path),
        ]
    return subprocess.list2cmdline(arguments)


def is_startup_enabled() -> bool:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
    except OSError:
        return False
    return bool(value)


def enable_startup(command: str) -> None:
    import winreg

    with winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
    ) as key:
        winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command)


def disable_startup() -> None:
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, VALUE_NAME)
    except OSError:
        pass
