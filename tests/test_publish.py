import json
import unittest
from urllib.parse import parse_qs, urlparse

from ntfy_clipboard.ntfy_client import publish_message


class PublishMessageTests(unittest.TestCase):
    def test_posts_message_and_returns_id(self):
        captured = {}

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps({"id": "new-id"}).encode("utf-8")

        def opener(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return Response()

        message_id = publish_message(
            server="https://ntfy.sh",
            topic="sms",
            message="验证码 123456",
            title="短信",
            opener=opener,
        )

        request = captured["request"]
        self.assertEqual(message_id, "new-id")
        self.assertEqual(request.get_method(), "POST")
        parsed = urlparse(request.full_url)
        self.assertEqual(parsed.path, "/sms")
        self.assertEqual(parse_qs(parsed.query)["title"], ["短信"])
        self.assertIsNone(request.get_header("Title"))
        self.assertEqual(request.data, "验证码 123456".encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
