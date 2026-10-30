import unittest

from SMS2Clip.app import ClipboardApp
from SMS2Clip.ntfy_client import NtfyMessage


class FakeClipboardWriter:
    def __init__(self):
        self.calls = []

    def copy_full_then_code(self, full_text, code):
        self.calls.append((full_text, code))


class FakeHistory:
    def __init__(self):
        self.calls = []

    def add(self, text, code, message_id):
        self.calls.append((text, code, message_id))


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

    def test_disabled_auto_copy_keeps_full_message_but_notification_can_copy_code(self):
        writer = FakeClipboardWriter()
        notifier = FakeNotifier()
        app = ClipboardApp(
            writer=writer,
            state=FakeState(),
            notifier=notifier,
            auto_copy_code=False,
        )

        app.handle_message(
            NtfyMessage(
                id="msg-manual",
                event="message",
                topic="test",
                title="短信",
                message="验证码为 482913",
            )
        )

        full_text = "短信\n验证码为 482913"
        self.assertEqual(writer.calls, [(full_text, None)])
        self.assertEqual(notifier.calls, [(full_text, "482913")])

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

    def test_records_every_message_in_history_even_without_a_code(self):
        writer = FakeClipboardWriter()
        history = FakeHistory()
        app = ClipboardApp(writer=writer, state=FakeState(), history=history)

        app.handle_message(
            NtfyMessage(
                id="msg-code",
                event="message",
                topic="test",
                title="短信",
                message="验证码为 123456",
            )
        )
        app.handle_message(
            NtfyMessage(
                id="msg-plain",
                event="message",
                topic="test",
                title="通知",
                message="您的快递已到达",
            )
        )

        self.assertEqual(
            history.calls,
            [
                ("短信\n验证码为 123456", "123456", "msg-code"),
                ("通知\n您的快递已到达", None, "msg-plain"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
