# AI Signal Scout

**AI Signal Scout** is an autonomous intelligence agent that discovers the most valuable AI ecosystem signals, evaluates their significance, and delivers a daily Top-5 Persian intelligence report to a private Telegram channel.

## Pipeline Architecture

The agent operates as a linear, modular pipeline:

```
sources.yaml -> RSS Collector -> SQLite Storage -> Gemini Sieve (Filter) -> Gemini Scout (Scoring) -> Persian Reporter -> Telegram Bot
```

1. **Collection Layer**: Ingests feeds from official AI lab blogs, arXiv, security feeds, and agent ecosystems configured in `sources.yaml`.
2. **Deduplication & Storage**: Hashes URLs and ignores duplicates using SQLite persistence (`data/signals.db`).
3. **Stage 1 (Sieve Filter)**: Uses Gemini 1.5 Flash for low-cost noise reduction (KEEP/DISCARD classification).
4. **Stage 2 (Scout Analysis)**: Performs deep analysis using Gemini 1.5 Flash to score candidates based on 6 weighted criteria (Capability Shift 25%, Real World Impact 20%, Agent Relevance 20%, X Discussion Potential 15%, Novelty 10%, Source Quality 10%).
5. **Persian Reporter**: Formats top 5 signals into structured Persian intelligence sections (`عنوان`, `امتیاز`, `چه اتفاقی افتاد`, `چرا مهم است`, `ELI5`, `چرا برای X مهم است`, `منبع`).
6. **Telegram Emitter**: Delivers formatted reports to a private Telegram channel with automatic message length validation and chunking.

---

## Required Environment Variables

Set the following environment variables (or place them in a `.env` file for local runs):

| Variable | Description | Required |
| --- | --- | --- |
| `GOOGLE_API_KEY` | Google Gemini API key for Sieve and Scout intelligence | Yes |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot token from @BotFather | Yes |
| `TELEGRAM_CHANNEL_ID` | Private Telegram channel ID (e.g., `-1001234567890`) | Yes |

---

## Local Execution

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Credentials
Create a `.env` file in the project root:
```env
GOOGLE_API_KEY=your_gemini_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHANNEL_ID=-100xxxxxxxxxx
```

### 3. Run Pipeline
```bash
python src/main.py
```

### 4. Run Tests
```bash
python -m unittest discover tests
```

---

## GitHub Actions Automated Schedule

The agent is fully automated via GitHub Actions:

- **Schedule**: Every day at **21:00 Tehran Time (UTC+3:30)** / **17:30 UTC daily** (`30 17 * * *`).
- **Workflow File**: `.github/workflows/daily_agent.yml`
- **Manual Trigger**: Can be manually triggered at any time via GitHub Actions `workflow_dispatch`.

### Required GitHub Repository Secrets
Add the following under **Settings > Secrets and variables > Actions**:
- `GOOGLE_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHANNEL_ID`

---

## License

MIT
