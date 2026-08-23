import asyncio
import os
from src.config.config_loader import load_sources
from src.collectors.rss_collector import collect_rss
from src.storage.database import init_db
from src.intelligence.sieve import run_sieve
from src.intelligence.scout import run_scout
from src.reporting.formatter import format_persian_report
from src.reporting.telegram import TelegramClient
from src.storage.operations import get_top_scored_signals
import json

async def main():
    print("🚀 Starting AI Signal Scout Validation")
    
    # 1. Init DB
    init_db()
    
    # 2. Collect
    print("📡 Collecting signals...")
    sources = load_sources()
    for source in sources:
        print(f"  Fetching {source.name}...")
        collect_rss(source)
    
    # 3. Sieve
    print("🔍 Running Sieve (Filter)...")
    await run_sieve()
    
    # 4. Scout
    print("🧠 Running Scout (Analysis)...")
    await run_scout()
    
    # 5. Report & Send
    print("📝 Generating Report...")
    top_signals = get_top_scored_signals(5)
    
    # Convert DB rows to Dicts for formatter
    # Row: (id, title, url, score, fingerprint, analysis_json, reported_at)
    formatted_signals = []
    for row in top_signals:
        analysis = json.loads(row[5])
        formatted_signals.append(analysis)
        
    report = format_persian_report(formatted_signals)
    print("\n--- REPORT PREVIEW ---")
    print(report)
    print("--- END PREVIEW ---\n")
    
    # 6. Telegram
    print("📤 Sending to Telegram...")
    client = TelegramClient()
    success = client.send_message(report)
    
    if success:
        print("✅ End-to-End Validation Successful!")
    else:
        print("❌ Telegram Delivery Failed!")

if __name__ == "__main__":
    asyncio.run(main())