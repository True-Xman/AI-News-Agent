"""
Telegram Client for AI Signal Scout.
Sends formatted reports to a private Telegram channel.
"""

import os
import logging
from httpx import Client, HTTPError
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TelegramClient:
    """
    A client to send messages to a Telegram channel using the Bot API.
    """

    BASE_URL = "https://api.telegram.org/bot"
    MAX_MESSAGE_LENGTH = 4096

    def __init__(self, bot_token: Optional[str] = None, channel_id: Optional[str] = None):
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.channel_id = channel_id or os.environ.get("TELEGRAM_CHANNEL_ID")

        if not self.bot_token:
            raise ValueError("Telegram Bot Token not provided. Set TELEGRAM_BOT_TOKEN env var.")
        if not self.channel_id:
            raise ValueError("Telegram Channel ID not provided. Set TELEGRAM_CHANNEL_ID env var.")

        self.api_url = f"{self.BASE_URL}{self.bot_token}/sendMessage"

    def _escape_markdown_v2(self, text: str) -> str:
        """Escape special characters for MarkdownV2 formatting."""
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        return ''.join(f'\\{char}' if char in escape_chars else char for char in text)

    def _split_message(self, text: str) -> list:
        """
        Split a long message into chunks under Telegram's character limit.
        Prioritizes splitting at newlines.
        """
        if len(text) <= self.MAX_MESSAGE_LENGTH:
            return [text]

        chunks = []
        while len(text) > self.MAX_MESSAGE_LENGTH:
            # Find the last newline before the limit
            split_index = text.rfind('\n', 0, self.MAX_MESSAGE_LENGTH)
            if split_index == -1:
                # No newline found, just split at the limit
                split_index = self.MAX_MESSAGE_LENGTH

            chunks.append(text[:split_index])
            text = text[split_index:].lstrip('\n')

        chunks.append(text)
        return chunks

    def send_message(self, text: str) -> bool:
        """
        Send a text message to the configured Telegram channel.
        Handles splitting for long messages and MarkdownV2 escaping.
        Args:
            text: The message text to send.
        Returns:
            True if the message was sent successfully, False otherwise.
        """
        try:
            # Note: We are sending plain text to avoid escaping issues.
            # If we were to use MarkdownV2, we would escape the text here.
            # For now, plain text is safer with the Persian content.
            chunks = self._split_message(text)

            for chunk in chunks:
                payload = {
                    "chat_id": self.channel_id,
                    "text": chunk,
                    # "parse_mode": "MarkdownV2",  # Enable if escaping is handled correctly
                }

                with Client(timeout=30.0) as client:
                    response = client.post(self.api_url, json=payload)
                    response.raise_for_status()

                result = response.json()
                if not result.get("ok"):
                    error = result.get("description", "Unknown error")
                    logger.error(f"Telegram API error: {error}")
                    return False

                logger.info(f"Message sent successfully. Message ID: {result['result']['message_id']}")

            return True

        except HTTPError as e:
            logger.error(f"HTTP error sending message: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending message: {e}")
            return False

    def validate_payload(self, text: str) -> dict:
        """
        Validate and prepare the payload for sending.
        Useful for testing.
        """
        chunks = self._split_message(text)
        payloads = []
        for chunk in chunks:
            payloads.append({
                "chat_id": self.channel_id,
                "text": chunk,
            })
        return {"messages": payloads, "total_chunks": len(chunks)}


if __name__ == "__main__":
    # Example usage (requires env vars set)
    pass