"""Privacy-safe delivery of one validated HTML report to Telegram."""

import logging
import os

import httpx

from ..errors import ConfigurationError


logger = logging.getLogger(__name__)
# Telegram credentials are embedded in the Bot API URL, so third-party request
# logging must never emit that URL. This module provides its own sanitized logs.
logging.getLogger("httpx").setLevel(logging.WARNING)


class TelegramClient:
    BASE_URL = "https://api.telegram.org/bot"
    MAX_MESSAGE_LENGTH = 4096

    def __init__(self, bot_token: str | None = None, channel_id: str | None = None):
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.channel_id = channel_id or os.environ.get("TELEGRAM_CHANNEL_ID")
        if not self.bot_token:
            raise ConfigurationError(
                "TELEGRAM_BOT_TOKEN is required when report delivery is enabled"
            )
        if not self.channel_id:
            raise ConfigurationError(
                "TELEGRAM_CHANNEL_ID is required when report delivery is enabled"
            )
        self.api_url = f"{self.BASE_URL}{self.bot_token}/sendMessage"

    def send_message(self, text: str, client: httpx.Client | None = None) -> bool:
        """Send exactly one HTML message without logging its content or identifiers."""
        if not text or len(text) > self.MAX_MESSAGE_LENGTH:
            logger.error("Telegram delivery rejected an invalid message length")
            return False

        payload = {
            "chat_id": self.channel_id,
            "text": text,
            "parse_mode": "HTML",
            "link_preview_options": {"is_disabled": True},
        }
        owns_client = client is None
        request_client = client or httpx.Client(timeout=30.0)
        try:
            response = request_client.post(self.api_url, json=payload)
            response.raise_for_status()
            result = response.json()
            if not result.get("ok"):
                logger.error("Telegram API rejected the report")
                return False
            logger.info("Telegram accepted one report message")
            return True
        except httpx.HTTPError as exc:
            logger.error("Telegram delivery failed: %s", type(exc).__name__)
            return False
        except (TypeError, ValueError) as exc:
            logger.error("Telegram response validation failed: %s", type(exc).__name__)
            return False
        finally:
            if owns_client:
                request_client.close()
