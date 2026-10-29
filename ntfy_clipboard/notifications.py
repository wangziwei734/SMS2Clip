"""Windows toast notifications for incoming SMS messages."""

from __future__ import annotations

import ctypes
import logging
import sys
import threading
from typing import Callable

from .clipboard import set_clipboard_text
from .i18n import normalize_language, tr

try:
    from windows_toasts import (
        InteractableWindowsToaster,
        Toast,
        ToastButton,
        ToastDuration,
    )
except ImportError:  # pragma: no cover - optional on non-Windows builds
    InteractableWindowsToaster = None
    Toast = None
    ToastButton = None
    ToastDuration = None


APP_DISPLAY_NAME = "Ntfy Clipboard"
TOAST_GROUP = "ntfy-clipboard"


class ToastNotifier:
    """Show SMS notifications and handle their action buttons."""

    def __init__(
        self,
        language: str = "zh-CN",
        toaster=None,
        clipboard_setter: Callable[[str], None] = set_clipboard_text,
        message_shower: Callable[[str, str], None] | None = None,
        logger: logging.Logger | None = None,
        sms_delay_seconds: float = 8.0,
        scheduler: Callable[[float, Callable[[], None]], None] | None = None,
    ) -> None:
        self.language = normalize_language(language)
        self.logger = logger or logging.getLogger(__name__)
        self._clipboard_setter = clipboard_setter
        self._message_shower = message_shower or self._show_message_box
        self._active_toasts: list[object] = []
        self._timers: list[threading.Timer] = []
        self._sms_delay_seconds = sms_delay_seconds
        self._scheduler = scheduler or self._schedule_timer
        self._toaster = toaster
        if (
            self._toaster is None
            and sys.platform == "win32"
            and InteractableWindowsToaster
        ):
            try:
                self._toaster = InteractableWindowsToaster(APP_DISPLAY_NAME)
            except Exception:
                self.logger.exception(
                    "Could not initialize Windows toast notifications"
                )

    def _t(self, key: str, **values: object) -> str:
        return tr(self.language, key, **values)

    def notify_message(self, full_text: str, code: str | None) -> None:
        """Show the SMS toast and, if a code exists, the copied-code toast."""

        if code:
            self._show_copied_toast(code, full_text)
            self._scheduler(
                self._sms_delay_seconds,
                lambda: self._show_sms_toast(full_text, code),
            )
        else:
            self._show_sms_toast(full_text, None)

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

    def _show_copied_toast(self, code: str, full_text: str) -> None:
        if self._toaster is None or Toast is None:
            return
        actions = []
        if ToastButton is not None:
            actions.append(ToastButton(self._t("notify.view_full"), "view_full"))
        toast = Toast(
            [self._t("notify.copied_title", code=code), self._t("notify.copied_body")],
            duration=ToastDuration.Short,
            group=TOAST_GROUP,
            actions=actions,
        )
        toast.on_activated = lambda args: self._on_view_activated(args, full_text)
        self._show(toast)

    def _on_sms_activated(self, args, code: str | None, full_text: str) -> None:
        if code and getattr(args, "arguments", None) == "copy_code":
            self._clipboard_setter(code)
            self._show_copied_toast(code, full_text)
            return
        self._show_full_message(full_text)

    def _on_view_activated(self, args, full_text: str) -> None:
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

    def _schedule_timer(self, delay: float, callback: Callable[[], None]) -> None:
        timer = threading.Timer(delay, callback)
        timer.daemon = True
        timer.start()
        self._timers.append(timer)

    def close(self) -> None:
        for timer in self._timers:
            timer.cancel()
        self._timers.clear()
        if self._toaster is not None and hasattr(self._toaster, "clear_toasts"):
            try:
                self._toaster.clear_toasts()
            except Exception:
                self.logger.debug("Could not clear toast notifications", exc_info=True)

    def _show_message_box(self, title: str, text: str) -> None:
        if sys.platform != "win32":
            return
        try:
            ctypes.windll.user32.MessageBoxW(0, text, title, 0x00000040)
        except Exception:
            self.logger.exception("Could not show full SMS message box")
