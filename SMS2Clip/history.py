"""Persistent history of received ntfy messages."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

MAX_HISTORY_ENTRIES = 200


class HistoryStore:
    def __init__(
        self, path: str | Path, max_entries: int = MAX_HISTORY_ENTRIES
    ) -> None:
        self.path = Path(path)
        self.max_entries = max(1, max_entries)

    def load(self) -> list[dict[str, Any]]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return []
        if not isinstance(payload, list):
            return []
        records = [
            item for item in payload if isinstance(item, dict) and "text" in item
        ]
        return records[: self.max_entries]

    def add(
        self,
        text: str,
        code: str | None,
        message_id: str | None = None,
        received_at: str | None = None,
    ) -> dict[str, Any]:
        entry = {
            "id": message_id or "",
            "received_at": received_at
            or datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S"),
            "text": text,
            "code": code or "",
        }
        records = [entry, *self.load()]
        self._save(records[: self.max_entries])
        return entry

    def clear(self) -> None:
        self._save([])

    def _save(self, records: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(records, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)
