"""Runtime paths and migration from portable/legacy configuration."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

APP_DIR_NAME = "SMS2Clip"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", app_dir()))
    return base / relative


def _roaming_app_data_root() -> Path:
    roaming = os.environ.get("APPDATA")
    if roaming:
        roaming_path = Path(roaming)
        normalized = str(roaming_path).replace("/", "\\").lower()
        if (
            "\\appdata\\local\\packages\\" in normalized
            and "\\localcache\\roaming" in normalized
        ):
            profile = os.environ.get("USERPROFILE") or str(Path.home())
            return Path(profile) / "AppData" / "Roaming"
        return roaming_path
    return Path.home() / "AppData" / "Roaming"


def app_data_dir() -> Path:
    return _roaming_app_data_root() / APP_DIR_NAME


def start_menu_shortcut_path() -> Path:
    return (
        _roaming_app_data_root()
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / "SMS2Clip.lnk"
    )


def default_config_path() -> Path:
    if not is_frozen():
        return app_dir() / "config.json"

    target_dir = app_data_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "config.json"
    legacy = app_dir() / "config.json"

    if not target.exists() and legacy.exists():
        shutil.copy2(legacy, target)
        legacy_state = app_dir() / "state.json"
        target_state = target_dir / "state.json"
        if legacy_state.exists() and not target_state.exists():
            shutil.copy2(legacy_state, target_state)

    return target
