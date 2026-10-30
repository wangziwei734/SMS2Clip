"""Windows login-startup registration using the HKCU Run key."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

VALUE_NAME = "SMS2Clip"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def build_startup_command(
    frozen: bool,
    executable: Path,
    config_path: Path,
    mode: str = "manager",
) -> str:
    if mode == "service":
        if frozen:
            arguments = [str(executable), "--service", "--config", str(config_path)]
        else:
            arguments = [
                str(executable),
                "-m",
                "SMS2Clip",
                "--service",
                "--config",
                str(config_path),
            ]
    elif mode == "manager":
        if frozen:
            arguments = [str(executable), "--minimized", "--config", str(config_path)]
        else:
            arguments = [
                str(executable),
                "-m",
                "SMS2Clip.gui",
                "--minimized",
                "--config",
                str(config_path),
            ]
    else:
        raise ValueError(f"unsupported startup mode: {mode}")
    return subprocess.list2cmdline(arguments)


def _read_startup_command() -> str | None:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
    except OSError:
        return None
    return str(value) if value else None


def startup_mode_from_command(command: str | None) -> str:
    if not command:
        return "manual"
    try:
        arguments = shlex.split(command, posix=False)
    except ValueError:
        arguments = command.split()
    return "service" if "--service" in arguments else "manager"


def get_startup_mode() -> str:
    return startup_mode_from_command(_read_startup_command())


def is_startup_enabled() -> bool:
    return get_startup_mode() != "manual"


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
