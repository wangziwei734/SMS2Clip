import io
import json
import unittest
from urllib.parse import parse_qs, urlparse

from ntfy_clipboard.ntfy_client import (
    NtfySubscriber,
    build_subscribe_url,
    parse_message,
)


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


class NtfyClientTests(unittest.TestCase):
    def test_parses_message_event(self):
        line = json.dumps(
            {
                "id": "abc123",
                "event": "message",
                "topic": "sms",
                "title": "短信",
                "message": "验证码 482913",
            }
        ).encode("utf-8")

        message = parse_message(line)

        self.assertIsNotNone(message)
        self.assertEqual(message.id, "abc123")
        self.assertEqual(message.title, "短信")
        self.assertEqual(message.message, "验证码 482913")

    def test_ignores_keepalive_event(self):
        self.assertIsNone(parse_message(b'{"event":"keepalive"}'))

    def test_builds_subscribe_url_with_since(self):
        url = build_subscribe_url("https://ntfy.sh/", "my-topic", since="msg-1")
        parsed = urlparse(url)

        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "ntfy.sh")
        self.assertEqual(parsed.path, "/my-topic/json")
        self.assertEqual(parse_qs(parsed.query)["since"], ["msg-1"])

    def test_subscriber_yields_only_message_events(self):
        payload = (
            '{"event":"open","id":"x"}\n'
            '{"event":"keepalive","id":"y"}\n'
            '{"id":"msg-1","event":"message","topic":"sms","message":"验证码 123456"}\n'
        ).encode("utf-8")
        subscriber = NtfySubscriber(
            server="https://ntfy.sh",
            topic="sms",
            opener=lambda request, timeout: FakeResponse(payload),
        )

        messages = list(subscriber.iter_messages())

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].id, "msg-1")
        self.assertEqual(messages[0].message, "验证码 123456")


if __name__ == "__main__":
    unittest.main()
