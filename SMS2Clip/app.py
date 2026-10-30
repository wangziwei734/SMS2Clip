"""Application logic that turns ntfy messages into clipboard contents."""

from __future__ import annotations

import logging

from .extractor import extract_verification_code
from .ntfy_client import NtfyMessage


def compose_full_message(message: NtfyMessage) -> str:
    if message.title and message.message:
        return f"{message.title}\n{message.message}"
    return message.message or message.title


class ClipboardApp:
    def __init__(
        self,
        writer,
        state,
        logger: logging.Logger | None = None,
        notifier=None,
        auto_copy_code: bool = True,
        history=None,
    ) -> None:
        self.writer = writer
        self.state = state
        self.logger = logger or logging.getLogger(__name__)
        self.notifier = notifier
        self.auto_copy_code = auto_copy_code
        self.history = history

    def handle_message(self, message: NtfyMessage) -> bool:
        if message.id and self.state.last_id == message.id:
            self.logger.debug("Ignoring duplicate ntfy message %s", message.id)
            return False

        full_text = compose_full_message(message)
        code = extract_verification_code(full_text)
        if self.history is not None:
            try:
                self.history.add(full_text, code, message.id)
            except Exception:
                self.logger.exception("Could not save message history")
        self.writer.copy_full_then_code(
            full_text, code if self.auto_copy_code else None
        )

        if self.notifier is not None:
            try:
                self.notifier.notify_message(full_text, code)
            except Exception:
                self.logger.exception("Could not show message notification")

        if message.id:
            self.state.last_id = message.id
            self.state.save()

        self.logger.info(
            "Copied message %s; verification code: %s",
            message.id or "(no id)",
            "found" if code else "not found",
        )
        return True
