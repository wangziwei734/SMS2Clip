"""Long-running reconnect loop for the clipboard bridge."""

from __future__ import annotations

import logging
import time
from typing import Callable

from .app import ClipboardApp
from .clipboard import ClipboardWriter
from .config import Config
from .notifications import ToastNotifier
from .ntfy_client import NtfySubscriber
from .state import StateStore


def run_service(
    config: Config,
    logger: logging.Logger,
    subscriber_factory: Callable[[str | None], NtfySubscriber] | None = None,
    notifier_factory: Callable[[], ToastNotifier] | None = None,
) -> None:
    state = StateStore(config.state_file).load()
    writer = ClipboardWriter(gap_seconds=config.clipboard_gap_ms / 1000)
    if notifier_factory is None:

        def notifier_factory() -> ToastNotifier:
            return ToastNotifier(language=config.language, logger=logger)

    notifier = notifier_factory()
    app = ClipboardApp(
        writer=writer,
        state=state,
        logger=logger,
        notifier=notifier,
    )

    if subscriber_factory is None:

        def subscriber_factory(since: str | None) -> NtfySubscriber:
            return NtfySubscriber(
                server=config.server,
                topic=config.topic,
                since=since,
                token=config.token,
                username=config.username,
                password=config.password,
            )

    backoff = config.reconnect_min_seconds
    logger.info("Starting ntfy clipboard bridge for %s/%s", config.server, config.topic)
    try:
        while True:
            since = state.last_id or config.since
            try:
                subscriber = subscriber_factory(since)
                for message in subscriber.iter_messages():
                    app.handle_message(message)
                backoff = config.reconnect_min_seconds
            except KeyboardInterrupt:
                logger.info("Stopping ntfy clipboard bridge")
                return
            except Exception:
                logger.exception(
                    "ntfy connection failed; retrying in %.1f seconds", backoff
                )

            time.sleep(backoff)
            backoff = min(backoff * 2, config.reconnect_max_seconds)
    finally:
        close = getattr(notifier, "close", None)
        if close is not None:
            close()
