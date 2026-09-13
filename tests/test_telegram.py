import json
import unittest

import httpx

from src.reporting.telegram import TelegramClient


REPORT = (
    "<b>AI SIGNAL SCOUT</b>\n"
    "AUTONOMOUS AI INTELLIGENCE BRIEF\n"
    "2026-09-13 UTC · TOP 1\n"
    "<b>1 · 84.5/100 · Verified capability update</b>\n"
    'Why: A verified workflow changed. · <a href="https://source.example/item">Source ↗</a>\n'
    "Live RSS → Gemini analysis → deterministic ranking → Telegram"
)


class TelegramClientTests(unittest.TestCase):
    def test_sends_one_html_message_without_link_preview(self):
        payloads = []

        def handler(request):
            payloads.append(json.loads(request.content))
            return httpx.Response(200, json={"ok": True, "result": {"message_id": 987654}})

        transport = httpx.MockTransport(handler)
        telegram = TelegramClient("secret-bot-token", "private-channel-id")
        with httpx.Client(transport=transport) as client:
            with self.assertLogs(level="INFO") as captured:
                sent = telegram.send_message(REPORT, client=client)

        self.assertTrue(sent)
        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0]["text"], REPORT)
        self.assertEqual(payloads[0]["parse_mode"], "HTML")
        self.assertEqual(payloads[0]["link_preview_options"], {"is_disabled": True})
        logs = "\n".join(captured.output)
        for private_value in (
            "secret-bot-token",
            "private-channel-id",
            "https://source.example/item",
            "Verified capability update",
            "987654",
        ):
            self.assertNotIn(private_value, logs)

    def test_api_rejection_returns_false_without_logging_response_details(self):
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"ok": False, "description": "private diagnostic detail"},
            )
        )
        telegram = TelegramClient("secret-bot-token", "private-channel-id")
        with httpx.Client(transport=transport) as client:
            with self.assertLogs("src.reporting.telegram", level="ERROR") as captured:
                sent = telegram.send_message(REPORT, client=client)

        self.assertFalse(sent)
        self.assertNotIn("private diagnostic detail", "\n".join(captured.output))


if __name__ == "__main__":
    unittest.main()
