"""Command-line entry point for ntfy-clipboard."""

from __future__ import annotations

import argparse
import json
import logging
import secrets
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import Config
from .extractor import extract_verification_code
from .ntfy_client import publish_message
from .service import run_service


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ntfy-clipboard",
        description="Copy SMS messages received through ntfy into the Windows clipboard.",
    )
    parser.add_argument("--config", default="config.json", help="Path to config.json")
    parser.add_argument(
        "--extract", metavar="TEXT", help="Test code extraction and exit"
    )
    parser.add_argument(
        "--send", metavar="TEXT", help="Publish a test message to ntfy and exit"
    )
    parser.add_argument("--title", default="短信", help="Title used with --send")
    parser.add_argument("--init", action="store_true", help="Create a new config.json")
    parser.add_argument("--force", action="store_true", help="Overwrite with --init")
    parser.add_argument(
        "--check", action="store_true", help="Validate configuration and exit"
    )
    parser.add_argument("--service", action="store_true", help=argparse.SUPPRESS)
    return parser


def _create_config(path: Path, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"{path} already exists; use --force to overwrite it")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "server": "https://ntfy.sh",
        "topic": secrets.token_urlsafe(12),
        "token": "",
        "username": "",
        "password": "",
        "since": "",
        "clipboard_gap_ms": 350,
        "state_file": "state.json",
        "log_file": "logs/ntfy-clipboard.log",
        "reconnect_min_seconds": 1,
        "reconnect_max_seconds": 60,
        "language": "zh-CN",
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Created {path}")
    print(f"Topic: {payload['topic']}")
    print(f"Publish URL: {payload['server']}/{payload['topic']}")


def _configure_logging(config: Config) -> logging.Logger:
    config.log_file.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ntfy_clipboard")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    handler = RotatingFileHandler(
        config.log_file,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if args.extract is not None:
        code = extract_verification_code(args.extract)
        print(code if code else "NOT_FOUND")
        return 0

    config_path = Path(args.config)

    if args.init:
        try:
            _create_config(config_path, force=args.force)
        except FileExistsError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0

    try:
        config = Config.load(config_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    if args.check:
        print(f"OK server={config.server} topic={config.topic}")
        return 0

    if args.send is not None:
        try:
            message_id = publish_message(
                server=config.server,
                topic=config.topic,
                message=args.send,
                title=args.title,
                token=config.token,
                username=config.username,
                password=config.password,
            )
        except Exception as exc:
            print(f"Publish failed: {exc}", file=sys.stderr)
            return 3
        print(message_id)
        return 0

    logger = _configure_logging(config)
    try:
        run_service(config, logger)
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
