import json
import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from SMS2Clip.config import Config
from SMS2Clip.ntfy_client import NtfyMessage
from SMS2Clip.service import run_service


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
                auto_copy_code=False,
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

            with patch("SMS2Clip.service.ClipboardWriter", return_value=writer):
                run_service(
                    config,
                    logging.getLogger("test-service"),
                    subscriber_factory=lambda since: FakeSubscriber(message),
                    notifier_factory=lambda: notifier,
                )

            self.assertEqual(writer.calls, [("短信\n验证码为 482913", None)])
            self.assertEqual(notifier.messages, [("短信\n验证码为 482913", "482913")])
            self.assertTrue(notifier.closed)
            saved = json.loads((base / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["last_id"], "msg-1")
            history = json.loads((base / "history.json").read_text(encoding="utf-8"))
            self.assertEqual(history[0]["text"], "短信\n验证码为 482913")
            self.assertEqual(history[0]["code"], "482913")


if __name__ == "__main__":
    unittest.main()
