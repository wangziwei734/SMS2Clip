"""ntfy publish and subscribe helpers."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Callable, Iterator
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class NtfyMessage:
    id: str
    event: str
    topic: str
    title: str = ""
    message: str = ""


def parse_message(raw: bytes | str) -> NtfyMessage | None:
    """Parse one ntfy JSON-stream line, returning only message events."""

    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict) or payload.get("event") != "message":
        return None
    if not payload.get("message"):
        return None

    return NtfyMessage(
        id=str(payload.get("id", "")),
        event="message",
        topic=str(payload.get("topic", "")),
        title=str(payload.get("title", "")),
        message=str(payload.get("message", "")),
    )


def build_subscribe_url(server: str, topic: str, since: str | None = None) -> str:
    base = server.rstrip("/")
    url = f"{base}/{quote(topic, safe='')}/json"
    if since:
        url += "?" + urlencode({"since": since})
    return url


def build_publish_url(server: str, topic: str, title: str = "") -> str:
    url = f"{server.rstrip('/')}/{quote(topic, safe='')}"
    if title:
        url += "?" + urlencode({"title": title})
    return url


def _auth_headers(
    token: str | None, username: str | None, password: str | None
) -> dict[str, str]:
    if token:
        return {"Authorization": f"Bearer {token}"}
    if username:
        credentials = base64.b64encode(
            f"{username}:{password or ''}".encode("utf-8")
        ).decode("ascii")
        return {"Authorization": f"Basic {credentials}"}
    return {}


class NtfySubscriber:
    def __init__(
        self,
        server: str,
        topic: str,
        since: str | None = None,
        token: str | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout: float = 90.0,
        opener: Callable[..., object] = urlopen,
    ) -> None:
        self.server = server
        self.topic = topic
        self.since = since
        self.token = token
        self.username = username
        self.password = password
        self.timeout = timeout
        self._opener = opener

    def iter_messages(self) -> Iterator[NtfyMessage]:
        headers = {
            "User-Agent": "sms2clip/0.4.0",
            "Accept": "application/x-ndjson",
        }
        headers.update(_auth_headers(self.token, self.username, self.password))
        request = Request(
            build_subscribe_url(self.server, self.topic, self.since),
            headers=headers,
        )
        with self._opener(request, timeout=self.timeout) as response:
            for raw_line in response:
                message = parse_message(raw_line)
                if message is not None:
                    yield message


def publish_message(
    server: str,
    topic: str,
    message: str,
    title: str = "",
    token: str | None = None,
    username: str | None = None,
    password: str | None = None,
    timeout: float = 15.0,
    opener: Callable[..., object] = urlopen,
) -> str:
    headers = {
        "User-Agent": "sms2clip/0.4.0",
        "Content-Type": "text/plain; charset=utf-8",
    }
    headers.update(_auth_headers(token, username, password))

    request = Request(
        build_publish_url(server, topic, title),
        data=message.encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with opener(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return str(payload.get("id", ""))
