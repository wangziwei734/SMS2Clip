import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from SMS2Clip.config import Config


class ConfigTests(unittest.TestCase):
    def _write_config(self, directory, overrides=None):
        payload = {
            "server": "https://ntfy.sh",
            "topic": "my-topic",
            "since": "10m",
        }
        if overrides:
            payload.update(overrides)
        path = Path(directory) / "config.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_loads_defaults_and_resolves_relative_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_config(directory)
            config = Config.load(path)

            self.assertEqual(config.topic, "my-topic")
            self.assertEqual(config.server, "https://ntfy.sh")
            self.assertEqual(config.clipboard_gap_ms, 350)
            self.assertTrue(config.auto_copy_code)
            self.assertEqual(
                config.state_file, (Path(directory) / "state.json").resolve()
            )
            self.assertEqual(
                config.log_file, (Path(directory) / "logs" / "sms2clip.log").resolve()
            )

    def test_loads_disabled_auto_copy_setting(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_config(directory, {"auto_copy_code": False})
            config = Config.load(path)

            self.assertFalse(config.auto_copy_code)

    def test_defaults_to_live_subscription_without_replaying_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                json.dumps({"server": "https://ntfy.sh", "topic": "my-topic"}),
                encoding="utf-8",
            )
            config = Config.load(path)
            self.assertEqual(config.since, "")

    def test_rejects_missing_topic(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_config(directory, {"topic": ""})
            with self.assertRaises(ValueError):
                Config.load(path)

    def test_environment_token_overrides_config_token(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_config(directory, {"token": "from-file"})
            with patch.dict(os.environ, {"NTFY_TOKEN": "from-env"}):
                config = Config.load(path)
            self.assertEqual(config.token, "from-env")


if __name__ == "__main__":
    unittest.main()
