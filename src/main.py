import asyncio
import logging
import os
import sys

# Configure UTF-8 for console output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from src.config.config_loader import load_sources
from src.collectors.rss_collector import collect_rss
from src.storage.database import init_db
from src.storage.operations import (
    get_top_scored_signals,
    get_unprocessed_raw_signals,
    get_keep_signals
)
from src.intelligence.sieve import run_sieve
from src.intelligence.scout import run_scout
from src.reporting.formatter import format_persian_report
from src.reporting.telegram import TelegramClient
import json

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AI-Signal-Scout")

async def run_pipeline():
    logger.info("Starting AI Signal Scout Pipeline...")

    # 1. Initialize Database
    init_db()

    # 2. Load Sources & Collect Signals
    sources = load_sources("sources.yaml")
    logger.info(f"Loaded {len(sources)} sources from configuration.")
    total_collected = 0
    for src in sources:
        try:
            signals = collect_rss(src)
            total_collected += len(signals)
            logger.info(f"Fetched {len(signals)} items from {src.name}")
        except Exception as e:
            logger.error(f"Error fetching source {src.name}: {e}")

    logger.info(f"Total raw signals collected in this run: {total_collected}")

    # 3. Sieve Noise Filtering (Gemini Flash)
    unprocessed = get_unprocessed_raw_signals(limit=50)
    if unprocessed:
        logger.info(f"Running Sieve filtering on {len(unprocessed)} raw signals...")
        success = await run_sieve()
        if not success:
            logger.error("Pipeline stopped due to Gemini quota exhaustion.")
            return
    else:
        logger.info("No unprocessed raw signals for Sieve filtering.")

    # 4. Scout Analysis & Scoring (Gemini Flash)
    keep_signals = get_keep_signals()
    if keep_signals:
        logger.info(f"Running Scout deep analysis on {len(keep_signals)} candidate signals...")
        await run_scout()
    else:
        logger.info("No candidate signals ready for Scout analysis.")

    # 5. Generate Persian Report
    top_rows = get_top_scored_signals(limit=5)
    if not top_rows:
        logger.warning("No scored signals available to generate report.")
        return

    formatted_signals = []
    for row in top_rows:
        # row[5] contains analysis_json string
        analysis_data = json.loads(row[5])
        formatted_signals.append(analysis_data)

    report_text = format_persian_report(formatted_signals)
    logger.info(f"Generated Persian report ({len(report_text)} chars).")

    # 6. Deliver to Telegram
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")

    if not bot_token or not channel_id:
        logger.warning("Telegram credentials not configured. Skipping delivery.")
        print("\n--- REPORT OUTPUT ---\n")
        print(report_text)
        print("\n---------------------\n")
        return

    client = TelegramClient(bot_token=bot_token, channel_id=channel_id)
    success = client.send_message(report_text)
    if success:
        logger.info("Report delivered successfully to Telegram!")
    else:
        logger.error("Failed to deliver report to Telegram.")

if __name__ == "__main__":
    asyncio.run(run_pipeline())
