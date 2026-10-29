"""Helpers for managing the background service process."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path


def build_service_command(
    config_path: Path,
    frozen: bool,
    executable: Path,
) -> list[str]:
    if frozen:
        return [str(executable), "--service", "--config", str(config_path)]
    return [
        str(executable),
        "-m",
        "ntfy_clipboard",
        "--service",
        "--config",
        str(config_path),
    ]


def pid_file_path(config_path: Path) -> Path:
    return config_path.parent / "ntfy-clipboard.pid"


def read_pid(path: Path) -> int | None:
    try:
        value = int(path.read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        return None
    return value if value > 0 else None


def process_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        process_query_limited_information = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(
            process_query_limited_information, False, pid
        )
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def terminate_process(pid: int) -> None:
    if pid <= 0 or not process_is_running(pid):
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/F", "/T"],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=False,
        )
        return
    os.kill(pid, 15)
