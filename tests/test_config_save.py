import json
import tempfile
import unittest
from pathlib import Path

from SMS2Clip.config import Config


class ConfigSaveTests(unittest.TestCase):
    def test_saves_and_reloads_config(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            config = Config(
                server="https://ntfy.sh",
                topic="my-topic",
                token="token",
                username="user",
                password="pass",
                since="",
                clipboard_gap_ms=500,
                state_file=base / "state.json",
                log_file=base / "logs" / "app.log",
                reconnect_min_seconds=1,
                reconnect_max_seconds=30,
            )
            path = base / "config.json"
            config.save(path)

            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["topic"], "my-topic")
            self.assertEqual(payload["clipboard_gap_ms"], 500)
            self.assertTrue(payload["auto_copy_code"])
            self.assertEqual(payload["state_file"], "state.json")
            self.assertEqual(payload["log_file"], str(Path("logs") / "app.log"))
            self.assertEqual(payload["language"], "zh-CN")

            loaded = Config.load(path)
            self.assertEqual(loaded.topic, "my-topic")
            self.assertEqual(loaded.token, "token")
            self.assertEqual(loaded.clipboard_gap_ms, 500)
            self.assertEqual(loaded.language, "zh-CN")

    def test_language_round_trips(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            config = Config(
                server="https://ntfy.sh",
                topic="my-topic",
                token=None,
                username=None,
                password=None,
                since="",
                clipboard_gap_ms=350,
                state_file=base / "state.json",
                log_file=base / "logs" / "app.log",
                reconnect_min_seconds=1,
                reconnect_max_seconds=30,
                language="en",
            )
            path = base / "config.json"
            config.save(path)
            self.assertEqual(Config.load(path).language, "en")

    def test_auto_copy_setting_round_trips(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            config = Config(
                server="https://ntfy.sh",
                topic="my-topic",
                token=None,
                username=None,
                password=None,
                since="",
                clipboard_gap_ms=350,
                state_file=base / "state.json",
                log_file=base / "logs" / "app.log",
                reconnect_min_seconds=1,
                reconnect_max_seconds=30,
                auto_copy_code=False,
            )
            path = base / "config.json"
            config.save(path)
            self.assertFalse(Config.load(path).auto_copy_code)


if __name__ == "__main__":
    unittest.main()
