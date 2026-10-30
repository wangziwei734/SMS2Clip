"""Configuration loading for the SMS2Clip bridge."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .i18n import normalize_language


@dataclass(frozen=True)
class Config:
    server: str
    topic: str
    token: str | None
    username: str | None
    password: str | None
    since: str
    clipboard_gap_ms: int
    state_file: Path
    log_file: Path
    reconnect_min_seconds: float
    reconnect_max_seconds: float
    language: str = "zh-CN"
    auto_copy_code: bool = True

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        config_path = Path(path).expanduser().resolve()
        payload: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))
        base = config_path.parent

        server = str(payload.get("server", "https://ntfy.sh")).rstrip("/")
        if not server.startswith(("https://", "http://")):
            raise ValueError("server must start with https:// or http://")

        topic = str(payload.get("topic", "")).strip()
        if not topic:
            raise ValueError("topic must not be empty")

        token = os.environ.get("NTFY_TOKEN") or payload.get("token") or None
        username = payload.get("username") or None
        password = payload.get("password") or None

        state_value = Path(str(payload.get("state_file", "state.json")))
        log_value = Path(str(payload.get("log_file", "logs/sms2clip.log")))
        state_file = state_value if state_value.is_absolute() else base / state_value
        log_file = log_value if log_value.is_absolute() else base / log_value

        gap = int(payload.get("clipboard_gap_ms", 350))
        if gap < 0:
            raise ValueError("clipboard_gap_ms must be zero or greater")

        auto_copy_code = payload.get("auto_copy_code", True)
        if isinstance(auto_copy_code, str):
            auto_copy_code = auto_copy_code.strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
        else:
            auto_copy_code = bool(auto_copy_code)

        reconnect_min = float(payload.get("reconnect_min_seconds", 1))
        reconnect_max = float(payload.get("reconnect_max_seconds", 60))
        if reconnect_min <= 0 or reconnect_max < reconnect_min:
            raise ValueError("reconnect intervals are invalid")

        return cls(
            server=server,
            topic=topic,
            token=str(token) if token else None,
            username=str(username) if username else None,
            password=str(password) if password else None,
            since=str(payload.get("since", "")),
            clipboard_gap_ms=gap,
            state_file=state_file,
            log_file=log_file,
            reconnect_min_seconds=reconnect_min,
            reconnect_max_seconds=reconnect_max,
            language=normalize_language(str(payload.get("language", "zh-CN"))),
            auto_copy_code=auto_copy_code,
        )

    def save(self, path: str | Path) -> None:
        config_path = Path(path).expanduser().resolve()
        base = config_path.parent
        config_path.parent.mkdir(parents=True, exist_ok=True)

        def relative_or_absolute(value: Path) -> str:
            try:
                return str(value.resolve().relative_to(base))
            except ValueError:
                return str(value.resolve())

        payload = {
            "server": self.server,
            "topic": self.topic,
            "token": self.token or "",
            "username": self.username or "",
            "password": self.password or "",
            "since": self.since,
            "clipboard_gap_ms": self.clipboard_gap_ms,
            "state_file": relative_or_absolute(self.state_file),
            "log_file": relative_or_absolute(self.log_file),
            "reconnect_min_seconds": self.reconnect_min_seconds,
            "reconnect_max_seconds": self.reconnect_max_seconds,
            "language": self.language,
            "auto_copy_code": self.auto_copy_code,
        }
        config_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
