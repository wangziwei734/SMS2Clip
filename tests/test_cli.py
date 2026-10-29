import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ntfy_clipboard.__main__ import main


class CliTests(unittest.TestCase):
    def test_extract_prints_code(self):
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["--extract", "验证码为 482913"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(output.getvalue().strip(), "482913")

    def test_extract_prints_not_found_for_text_without_code(self):
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["--extract", "您的快递已到达"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(output.getvalue().strip(), "NOT_FOUND")

    def test_send_reports_publish_failure_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            config_path.write_text(
                json.dumps({"server": "https://ntfy.sh", "topic": "sms"}),
                encoding="utf-8",
            )
            error = io.StringIO()
            with patch(
                "ntfy_clipboard.__main__.publish_message",
                side_effect=OSError("network down"),
            ):
                with redirect_stderr(error):
                    exit_code = main(
                        ["--config", str(config_path), "--send", "test message"]
                    )

        self.assertEqual(exit_code, 3)
        self.assertIn("Publish failed: network down", error.getvalue())


if __name__ == "__main__":
    unittest.main()
