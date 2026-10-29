import unittest

from ntfy_clipboard.app import ClipboardApp
from ntfy_clipboard.ntfy_client import NtfyMessage


class FakeClipboardWriter:
    def __init__(self):
        self.calls = []

    def copy_full_then_code(self, full_text, code):
        self.calls.append((full_text, code))


class FakeState:
    def __init__(self, last_id=None):
        self.last_id = last_id
        self.saved = 0

    def save(self):
        self.saved += 1


class FakeNotifier:
    def __init__(self):
        self.calls = []

    def notify_message(self, full_text, code):
        self.calls.append((full_text, code))


class ClipboardAppTests(unittest.TestCase):
    def test_copies_title_and_message_then_code(self):
        writer = FakeClipboardWriter()
        state = FakeState()
        app = ClipboardApp(writer=writer, state=state)

        handled = app.handle_message(
            NtfyMessage(
                id="msg-1",
                event="message",
                topic="test",
                title="短信",
                message="验证码为 482913，5分钟内有效。",
            )
        )

        self.assertTrue(handled)
        self.assertEqual(
            writer.calls,
            [("短信\n验证码为 482913，5分钟内有效。", "482913")],
        )
        self.assertEqual(state.last_id, "msg-1")
        self.assertEqual(state.saved, 1)

    def test_ignores_duplicate_message_id(self):
        writer = FakeClipboardWriter()
        state = FakeState(last_id="msg-1")
        app = ClipboardApp(writer=writer, state=state)

        handled = app.handle_message(
            NtfyMessage(
                id="msg-1",
                event="message",
                topic="test",
                title="",
                message="验证码为 482913",
            )
        )

        self.assertFalse(handled)
        self.assertEqual(writer.calls, [])

    def test_notifies_after_copying_message_and_code(self):
        writer = FakeClipboardWriter()
        notifier = FakeNotifier()
        app = ClipboardApp(writer=writer, state=FakeState(), notifier=notifier)

        app.handle_message(
            NtfyMessage(
                id="msg-2",
                event="message",
                topic="test",
                title="短信",
                message="验证码为 654321",
            )
        )

        self.assertEqual(notifier.calls, [("短信\n验证码为 654321", "654321")])


if __name__ == "__main__":
    unittest.main()
