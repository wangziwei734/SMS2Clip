import tempfile
import unittest
from pathlib import Path

from SMS2Clip.history import HistoryStore


class HistoryStoreTests(unittest.TestCase):
    def test_adds_newest_first_and_persists_messages_with_or_without_codes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            store = HistoryStore(path)
            store.add("验证码为 123456", "123456", "msg-1", "2026-10-30 10:00:00")
            store.add("您的快递已到达", None, "msg-2", "2026-10-30 10:01:00")

            records = HistoryStore(path).load()

            self.assertEqual([item["id"] for item in records], ["msg-2", "msg-1"])
            self.assertEqual(records[0]["code"], "")
            self.assertEqual(records[1]["code"], "123456")

    def test_keeps_only_the_latest_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            store = HistoryStore(Path(directory) / "history.json", max_entries=2)
            store.add("first", None, "1")
            store.add("second", None, "2")
            store.add("third", None, "3")

            self.assertEqual([item["id"] for item in store.load()], ["3", "2"])

    def test_clear_removes_all_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            store = HistoryStore(Path(directory) / "history.json")
            store.add("message", "1234", "msg-1")

            store.clear()

            self.assertEqual(store.load(), [])

    def test_corrupt_history_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            path.write_text("not json", encoding="utf-8")

            self.assertEqual(HistoryStore(path).load(), [])


if __name__ == "__main__":
    unittest.main()
