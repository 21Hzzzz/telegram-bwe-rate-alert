#!/usr/bin/env python3
"""Configure and run the BWE Telegram channel burst alert service."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from getpass import getpass
from pathlib import Path

from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError

from rate_monitor import BurstDetector

TARGET_CHANNEL = "https://t.me/BWE_pricechange_monitor"
DEFAULT_CONFIG = Path("/etc/telegram-bwe-rate-alert/config.json")
DEFAULT_SESSION = Path("/var/lib/telegram-bwe-rate-alert/telegram")
LOG = logging.getLogger("telegram_bwe_rate_alert")


def read_config(path: Path) -> dict[str, object]:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Cannot read configuration {path}: {error}") from error
    required = {"api_id", "api_hash", "phone", "webhook_url"}
    missing = required.difference(config)
    if missing:
        raise RuntimeError(f"Configuration misses: {', '.join(sorted(missing))}")
    return config


def validate_webhook(value: str) -> str:
    parsed = urllib.parse.urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Webhook URL must be a complete http(s) URL")
    return value.strip()


def prompt_configuration() -> dict[str, object]:
    phone = input("Telegram phone number (include country code, e.g. +8613800000000): ").strip()
    if not phone:
        raise ValueError("Telegram phone number cannot be empty")
    api_id_text = input("Telegram API ID: ").strip()
    try:
        api_id = int(api_id_text)
    except ValueError as error:
        raise ValueError("Telegram API ID must be an integer") from error
    api_hash = getpass("Telegram API Hash: ").strip()
    if not api_hash:
        raise ValueError("Telegram API Hash cannot be empty")
    webhook_url = validate_webhook(input("Alert webhook URL (HTTP GET): "))
    return {"api_id": api_id, "api_hash": api_hash, "phone": phone, "webhook_url": webhook_url}


def write_config(path: Path, config: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


async def configure(config_path: Path, session_path: Path) -> None:
    config = prompt_configuration()
    session_path.parent.mkdir(parents=True, exist_ok=True)
    client = TelegramClient(str(session_path), int(config["api_id"]), str(config["api_hash"]))
    await client.connect()
    try:
        if not await client.is_user_authorized():
            await client.send_code_request(str(config["phone"]))
            code = input("Telegram verification code: ").strip()
            try:
                await client.sign_in(phone=str(config["phone"]), code=code)
            except SessionPasswordNeededError:
                password = getpass("Telegram two-step verification password: ")
                await client.sign_in(password=password)
        await client.get_entity(TARGET_CHANNEL)
    finally:
        await client.disconnect()
    write_config(config_path, config)
    for file in session_path.parent.glob(session_path.name + "*"):
        os.chmod(file, 0o600)
    print(f"Telegram session saved. Ensure this account can access {TARGET_CHANNEL}.")


def send_webhook(url: str) -> None:
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": "telegram-bwe-rate-alert/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            LOG.info("Alert webhook returned HTTP %s", response.status)
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        LOG.error("Alert webhook request failed: %s", error)


async def run(config_path: Path, session_path: Path) -> None:
    config = read_config(config_path)
    detector = BurstDetector()
    client = TelegramClient(str(session_path), int(config["api_id"]), str(config["api_hash"]))

    @client.on(events.NewMessage(chats=TARGET_CHANNEL))
    async def channel_message(event: events.NewMessage.Event) -> None:
        if detector.record(time.monotonic()):
            LOG.warning("Burst detected: at least 5 messages within 60 seconds")
            await asyncio.to_thread(send_webhook, str(config["webhook_url"]))

    await client.start()
    if not await client.is_user_authorized():
        raise RuntimeError("Telegram session is not authorized; run the installer again")
    LOG.info("Monitoring %s", TARGET_CHANNEL)
    await client.run_until_disconnected()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("configure", "run"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--session", type=Path, default=DEFAULT_SESSION)
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    try:
        asyncio.run(configure(args.config, args.session) if args.command == "configure" else run(args.config, args.session))
    except (RuntimeError, ValueError) as error:
        LOG.error("%s", error)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
