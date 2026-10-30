import json
import tempfile
import unittest
from pathlib import Path

from SMS2Clip.state import StateStore


class StateStoreTests(unittest.TestCase):
    def test_missing_state_file_has_no_last_id(self):
        with tempfile.TemporaryDirectory() as directory:
            store = StateStore(Path(directory) / "state.json")
            store.load()
            self.assertIsNone(store.last_id)

    def test_round_trips_last_id(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            store = StateStore(path)
            store.last_id = "msg-123"
            store.save()

            loaded = StateStore(path)
            loaded.load()
            self.assertEqual(loaded.last_id, "msg-123")
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8"))["last_id"], "msg-123"
            )


if __name__ == "__main__":
    unittest.main()
