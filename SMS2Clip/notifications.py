"""Windows toast notifications for incoming SMS messages."""

from __future__ import annotations

import ctypes
import logging
import shutil
import sys
from pathlib import Path
from typing import Callable

from .clipboard import set_clipboard_text
from .i18n import normalize_language, tr
from .paths import app_data_dir, resource_path, start_menu_shortcut_path

try:
    from windows_toasts import (
        InteractableWindowsToaster,
        Toast,
        ToastButton,
    )
except ImportError:  # pragma: no cover - optional on non-Windows builds
    InteractableWindowsToaster = None
    Toast = None
    ToastButton = None


APP_DISPLAY_NAME = "SMS2Clip"
APP_AUMID = "SMS2Clip.Desktop"
TOAST_GROUP = "sms2clip"
MB_ICONINFORMATION = 0x00000040
MB_SETFOREGROUND = 0x00010000


def _register_start_menu_shortcut() -> None:
    if not getattr(sys, "frozen", False):
        return

    import gc

    import win32com.client
    from win32com.propsys import propsys, pscon

    shortcut_path = start_menu_shortcut_path()
    shortcut_path.parent.mkdir(parents=True, exist_ok=True)
    executable = Path(sys.executable).resolve()
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(str(shortcut_path))
    shortcut.TargetPath = str(executable)
    shortcut.WorkingDirectory = str(executable.parent)
    shortcut.IconLocation = str(executable)
    shortcut.Description = "SMS2Clip - iPhone SMS to Windows clipboard"
    shortcut.Save()
    shortcut = None
    shell = None
    gc.collect()

    store = propsys.SHGetPropertyStoreFromParsingName(
        str(shortcut_path), None, 2, propsys.IID_IPropertyStore
    )
    store.SetValue(
        pscon.PKEY_AppUserModel_ID,
        propsys.PROPVARIANTType(APP_AUMID),
    )
    store.Commit()
    store = None
    gc.collect()


def register_toast_identity() -> None:
    import winreg

    icon_path: Path | None = None
    try:
        source = resource_path("assets/sms2clip.ico")
        if source.exists():
            destination = app_data_dir() / "sms2clip.ico"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            icon_path = destination.resolve()
    except OSError:
        icon_path = None

    key_path = f"SOFTWARE\\Classes\\AppUserModelId\\{APP_AUMID}"
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path) as key:
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_DISPLAY_NAME)
        if icon_path is not None:
            winreg.SetValueEx(key, "IconUri", 0, winreg.REG_SZ, str(icon_path))
    _register_start_menu_shortcut()


class ToastNotifier:
    """Show SMS notifications and handle their action buttons."""

    def __init__(
        self,
        language: str = "zh-CN",
        toaster=None,
        clipboard_setter: Callable[[str], None] = set_clipboard_text,
        message_shower: Callable[[str, str], None] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.language = normalize_language(language)
        self.logger = logger or logging.getLogger(__name__)
        self._clipboard_setter = clipboard_setter
        self._message_shower = message_shower or self._show_message_box
        self._active_toasts: list[object] = []
        self._toaster = toaster
        if (
            self._toaster is None
            and sys.platform == "win32"
            and InteractableWindowsToaster
        ):
            try:
                register_toast_identity()
                self._toaster = InteractableWindowsToaster(APP_DISPLAY_NAME, APP_AUMID)
            except Exception:
                self.logger.exception(
                    "Could not initialize the SMS2Clip toast identity"
                )
                try:
                    self._toaster = InteractableWindowsToaster(APP_DISPLAY_NAME)
                except Exception:
                    self.logger.exception(
                        "Could not initialize Windows toast notifications"
                    )

    def _t(self, key: str, **values: object) -> str:
        return tr(self.language, key, **values)

    def notify_message(self, full_text: str, code: str | None) -> None:
        """Show the full SMS toast and a copy-code action when available."""

        self._show_sms_toast(full_text, code)

    def _show_sms_toast(self, full_text: str, code: str | None) -> None:
        if self._toaster is None or Toast is None:
            return
        actions = []
        if code and ToastButton is not None:
            actions.append(ToastButton(self._t("notify.copy"), "copy_code"))
        toast = Toast(
            [self._t("notify.sms_title"), full_text],
            group=TOAST_GROUP,
            actions=actions,
        )
        toast.on_activated = lambda args: self._on_sms_activated(args, code, full_text)
        self._show(toast)

    def _on_sms_activated(self, args, code: str | None, full_text: str) -> None:
        if code and getattr(args, "arguments", None) == "copy_code":
            self._clipboard_setter(code)
            return
        self._show_full_message(full_text)

    def _show_full_message(self, full_text: str) -> None:
        self._message_shower(self._t("notify.full_title"), full_text)

    def _show(self, toast) -> None:
        try:
            self._toaster.show_toast(toast)
            self._active_toasts.append(toast)
            if len(self._active_toasts) > 20:
                self._active_toasts = self._active_toasts[-20:]
        except Exception:
            self.logger.exception("Could not show Windows toast notification")

    def close(self) -> None:
        if self._toaster is not None and hasattr(self._toaster, "clear_toasts"):
            try:
                self._toaster.clear_toasts()
            except Exception:
                self.logger.debug("Could not clear toast notifications", exc_info=True)

    def _show_message_box(self, title: str, text: str) -> None:
        if sys.platform != "win32":
            return
        try:
            ctypes.windll.user32.MessageBoxW(
                0,
                text,
                title,
                MB_ICONINFORMATION | MB_SETFOREGROUND,
            )
        except Exception:
            self.logger.exception("Could not show full SMS message box")
