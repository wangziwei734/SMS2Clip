import json
import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ntfy_clipboard.config import Config
from ntfy_clipboard.ntfy_client import NtfyMessage
from ntfy_clipboard.service import run_service


class FakeWriter:
    def __init__(self):
        self.calls = []

    def copy_full_then_code(self, full_text, code):
        self.calls.append((full_text, code))


class FakeNotifier:
    def __init__(self):
        self.messages = []
        self.closed = False

    def notify_message(self, full_text, code):
        self.messages.append((full_text, code))

    def close(self):
        self.closed = True


class FakeSubscriber:
    def __init__(self, message):
        self.message = message

    def iter_messages(self):
        yield self.message
        raise KeyboardInterrupt


class ServiceTests(unittest.TestCase):
    def test_processes_a_message_then_saves_state(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            config = Config(
                server="https://ntfy.sh",
                topic="sms",
                token=None,
                username=None,
                password=None,
                since="",
                clipboard_gap_ms=350,
                state_file=base / "state.json",
                log_file=base / "log.txt",
                reconnect_min_seconds=1,
                reconnect_max_seconds=60,
            )
            writer = FakeWriter()
            notifier = FakeNotifier()
            message = NtfyMessage(
                id="msg-1",
                event="message",
                topic="sms",
                title="短信",
                message="验证码为 482913",
            )

            with patch("ntfy_clipboard.service.ClipboardWriter", return_value=writer):
                run_service(
                    config,
                    logging.getLogger("test-service"),
                    subscriber_factory=lambda since: FakeSubscriber(message),
                    notifier_factory=lambda: notifier,
                )

            self.assertEqual(writer.calls, [("短信\n验证码为 482913", "482913")])
            self.assertEqual(notifier.messages, [("短信\n验证码为 482913", "482913")])
            self.assertTrue(notifier.closed)
            saved = json.loads((base / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["last_id"], "msg-1")


if __name__ == "__main__":
    unittest.main()
