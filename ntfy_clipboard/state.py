"""Persistent state used to avoid replaying the same ntfy message twice."""

from __future__ import annotations

import json
import os
from pathlib import Path


class StateStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.last_id: str | None = None

    def load(self) -> "StateStore":
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            self.last_id = None
            return self

        last_id = payload.get("last_id") if isinstance(payload, dict) else None
        self.last_id = str(last_id) if last_id else None
        return self

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + ".tmp")
        temporary.write_text(
            json.dumps({"last_id": self.last_id}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary, self.path)
