import unittest

from SMS2Clip.clipboard import ClipboardWriter


class ClipboardWriterTests(unittest.TestCase):
    def test_copies_full_message_then_code(self):
        calls = []

        def set_text(text):
            calls.append(("set", text))

        def sleep(seconds):
            calls.append(("sleep", seconds))

        writer = ClipboardWriter(set_text=set_text, sleep=sleep, gap_seconds=0.35)
        writer.copy_full_then_code("完整短信内容", "123456")

        self.assertEqual(
            calls,
            [
                ("set", "完整短信内容"),
                ("sleep", 0.35),
                ("set", "123456"),
            ],
        )

    def test_copies_only_full_message_when_no_code_was_found(self):
        calls = []
        writer = ClipboardWriter(
            set_text=lambda text: calls.append(text),
            sleep=lambda seconds: self.fail(
                "sleep should not be called without a code"
            ),
        )

        writer.copy_full_then_code("没有验证码的短信", None)

        self.assertEqual(calls, ["没有验证码的短信"])


if __name__ == "__main__":
    unittest.main()
