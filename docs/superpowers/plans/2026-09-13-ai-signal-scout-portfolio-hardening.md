# AI Signal Scout Portfolio Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an English-first, cache-persistent, deterministically ranked AI Signal Scout whose tests, GitHub Actions runs, and sanitized artifacts provide truthful portfolio evidence.

**Architecture:** Curated RSS/Atom feeds are fetched with explicit health accounting, deduplicated in SQLite, filtered and analyzed through validated Gemini contracts, ranked in Python, formatted in English, and optionally delivered to Telegram. GitHub Actions restores and saves branch-scoped SQLite state and uploads a public-safe run summary that separates unit, offline, source-health, and live-service evidence.

**Tech Stack:** Python 3.11 in GitHub Actions, Python 3.14 for available local verification, `unittest`, `httpx`, `feedparser`, Pydantic v2, Google GenAI, SQLite, Telegram Bot API, YAML, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-13-ai-signal-scout-portfolio-hardening-design.md`

## Global Constraints

- English is the only production report language.
- `MAX_ITEM_AGE_DAYS = 7`, `SIEVE_INPUT_LIMIT = 50`, `SCOUT_INPUT_LIMIT = 15`, `REPORT_LIMIT = 5`, and `MAX_PER_SOURCE_FIRST_PASS = 2`.
- Snippets sent to Gemini are at most 1,500 characters; entries more than 24 hours in the future are rejected.
- The pipeline fails when fewer than 60 percent of configured feeds are healthy.
- Reports query the active `run_id` only and contain up to five items.
- SQLite cache saves occur only after a successful pipeline; same-ref runs are serialized.
- Unit and offline integration tests do not contact Gemini, Telegram, or live feeds.
- Sanitized evidence never includes report text, article snippets, secrets, Telegram identifiers, private project names, or local paths.
- No merge to `main` occurs without explicit user authorization in this chat.

---

### Task 1: Keyless Imports and Shared Failure Types

**Files:**
- Create: `src/errors.py`
- Create: `tests/test_gemini_client.py`
- Modify: `src/intelligence/gemini_client.py:1-38`
- Modify: `tests/test_main_pipeline.py:8-30`
- Modify: `requirements.txt:1-8`

**Interfaces:**
- Produces: `ConfigurationError`, `ExternalServiceError`, and `ResponseValidationError` exception classes.
- Produces: `create_gemini_client(api_key: str | None = None)` and `send_gemini_request(prompt: str, max_retries: int = 3, client_factory=None) -> str`.
- Preserves: importing `src.main`, Sieve, and Scout without environment credentials.

- [ ] **Step 1: Write tests that reproduce import-time credential failure**

```python
# tests/test_gemini_client.py
import asyncio
import importlib
import os
import unittest
from unittest.mock import patch


class GeminiClientTests(unittest.TestCase):
    def test_module_import_does_not_require_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            module = importlib.import_module("src.intelligence.gemini_client")
            importlib.reload(module)

    def test_request_without_api_key_raises_configuration_error(self):
        from src.errors import ConfigurationError
        from src.intelligence.gemini_client import send_gemini_request

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ConfigurationError, "GOOGLE_API_KEY"):
                asyncio.run(send_gemini_request("test"))
```

Update `test_main_imports` to import `src.main` under a cleared environment and remove the broad `try/except ImportError`, so the real traceback remains visible.

- [ ] **Step 2: Run the focused tests and confirm RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_gemini_client tests.test_main_pipeline -v
```

Expected: import fails because `genai.Client(...)` is created at module import, and `src.errors` does not yet exist.

- [ ] **Step 3: Add explicit errors and lazy Gemini construction**

```python
# src/errors.py
class PipelineError(RuntimeError):
    """Base error for an expected pipeline failure."""


class ConfigurationError(PipelineError):
    """Required runtime configuration is unavailable."""


class ExternalServiceError(PipelineError):
    """An external dependency did not complete successfully."""


class ResponseValidationError(PipelineError):
    """An external response violated the expected contract."""
```

Refactor `gemini_client.py` so no global client is created. `create_gemini_client` reads the passed key first, then `GOOGLE_API_KEY`, and raises `ConfigurationError("GOOGLE_API_KEY is required for live Gemini requests")` when absent. `send_gemini_request` constructs the client inside the coroutine, preserves exponential retries for temporary 429/503 responses, raises `ExternalServiceError` after retry exhaustion, and never prints credential values.

Remove the unused `openai` dependency and constrain runtime dependencies to compatible majors:

```text
httpx>=0.28,<1
pydantic>=2.12,<3
python-dotenv>=1.1,<2
pyyaml>=6,<7
feedparser>=6,<7
google-genai>=2,<3
```

- [ ] **Step 4: Verify GREEN and the full baseline**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_gemini_client tests.test_main_pipeline -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: keyless imports pass; all existing discoverable tests pass without a Gemini key.

- [ ] **Step 5: Commit the foundation**

```powershell
git add requirements.txt src/errors.py src/intelligence/gemini_client.py tests/test_gemini_client.py tests/test_main_pipeline.py
git commit -m "fix: make Gemini initialization lazy"
```

---

### Task 2: Persistent Storage and Run-Scoped Queries

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/helpers.py`
- Create: `tests/test_storage.py`
- Modify: `src/storage/database.py:1-69`
- Modify: `src/storage/operations.py:1-95`
- Modify: `src/models/raw_signal.py:1-18`

**Interfaces:**
- Consumes: `RawSignal` and a caller-provided `run_id`.
- Produces: `get_db_path() -> str`, `insert_raw_signal(signal, run_id) -> bool`, `get_unprocessed_raw_signals(run_id, limit=50) -> list[tuple]`, `get_keep_signals(run_id, limit=15) -> list[tuple]`, `get_top_scored_signals(run_id, limit=5) -> list[tuple]`, and `get_storage_counts() -> dict[str, int]`.
- Produces for tests: `TemporaryDatabaseTestCase` and `make_raw_signal(url, source="Test", source_id=1, found_at=None)` in `tests/helpers.py`.
- Preserves: the existing SQLite schema through idempotent migrations.

- [ ] **Step 1: Write failing storage tests with a temporary database**

```python
# tests/helpers.py
import os
import tempfile
import time
import unittest
from unittest.mock import patch

from src.models.raw_signal import RawSignal
from src.storage.database import init_db


class TemporaryDatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"SIGNALS_DB_PATH": os.path.join(self.tempdir.name, "signals.db")})
        self.env.start()
        init_db()

    def tearDown(self):
        self.env.stop()
        self.tempdir.cleanup()


def make_raw_signal(url, source="Test", source_id=1, found_at=None):
    return RawSignal(
        url=url,
        title=f"Signal from {source}",
        source=source,
        source_id=source_id,
        found_at=found_at or time.time(),
        snippet="Evidence-backed summary",
    )


# tests/test_storage.py
from tests.helpers import TemporaryDatabaseTestCase, make_raw_signal
from src.storage.operations import get_top_scored_signals, insert_processed_signal, insert_raw_signal


class StorageTests(TemporaryDatabaseTestCase):
    def test_insert_reports_new_then_duplicate(self):
        signal = make_raw_signal("https://example.com/one", source="A")
        self.assertTrue(insert_raw_signal(signal, "run-1"))
        self.assertFalse(insert_raw_signal(signal, "run-2"))

    def test_top_scores_are_scoped_to_run(self):
        insert_processed_signal("Old", "https://old", 99, "old", {"title": "Old"}, "old-run")
        insert_processed_signal("New", "https://new", 70, "new", {"title": "New"}, "new-run")
        rows = get_top_scored_signals("new-run", limit=5)
        self.assertEqual([row[1] for row in rows], ["New"])
```

Add a third test with rows from three sources to assert round-robin ordering and a hard retrieval limit.

- [ ] **Step 2: Run storage tests and confirm RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_storage -v
```

Expected: `insert_raw_signal` returns `None`, `SIGNALS_DB_PATH` is ignored, and `get_top_scored_signals` has no `run_id` argument.

- [ ] **Step 3: Implement dynamic database paths and deterministic queries**

```python
# src/storage/database.py
def get_db_path() -> str:
    return os.environ.get("SIGNALS_DB_PATH", "data/signals.db")


def get_connection():
    return sqlite3.connect(get_db_path())
```

Create the parent directory from `get_db_path()` in `init_db`. Add indexes for `raw_signals(run_id, filter_decision)`, `raw_signals(source_id, found_at)`, and `processed_signals(run_id, score)`.

Use `cursor.rowcount == 1` after `INSERT OR IGNORE` so `insert_raw_signal` returns an accurate new-versus-duplicate result. Scope filter updates by `url_hash` and `run_id`. Remove the invalid comparison between `raw_signals.url_hash` and `processed_signals.url`.

For balanced retrieval, query deterministically by `source_id`, `found_at DESC`, and `url_hash`, group rows by source, and consume one row per group per round until the limit is reached. `get_keep_signals` sorts by `filter_confidence DESC`, then recency before applying the same balancing rule.

- [ ] **Step 4: Verify storage behavior**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_storage -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: duplicate accounting, source balance, and current-run report isolation pass.

- [ ] **Step 5: Commit storage behavior**

```powershell
git add src/models/raw_signal.py src/storage/database.py src/storage/operations.py tests/__init__.py tests/helpers.py tests/test_storage.py
git commit -m "fix: make storage persistent and run scoped"
```

---

### Task 3: Source Health and Fresh RSS Collection

**Files:**
- Create: `tests/fixtures/sample_feed.xml`
- Create: `tests/test_rss_collector.py`
- Modify: `src/collectors/rss_collector.py:1-37`
- Modify: `src/config/config_loader.py:1-14`
- Modify: `sources.yaml:1-49`
- Modify: `src/utils/organization.py:1-35`
- Modify: `tests/test_organization.py:1-21`

**Interfaces:**
- Consumes: `SourceItem`, `run_id`, optional `httpx.Client`, and optional UTC `now`.
- Produces: `SourceCollectionResult(source_name, healthy, entries_parsed=0, recent_entries=0, inserted=0, duplicates=0, undated=0, error_category=None)`.
- Produces: `collect_rss(source_item, run_id, client=None, now=None) -> SourceCollectionResult`.

- [ ] **Step 1: Add a fixture and failing collector tests**

The fixture contains four entries: one current, one undated, one eight days old, and one more than 24 hours in the future.

```python
from datetime import datetime, timezone
from pathlib import Path

import httpx

from src.collectors.rss_collector import collect_rss
from src.config.config_loader import SourceItem
from tests.helpers import TemporaryDatabaseTestCase


FIXTURE_BYTES = Path("tests/fixtures/sample_feed.xml").read_bytes()


class RssCollectorTests(TemporaryDatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.now = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
        self.source = SourceItem(name="Fixture", url="https://feed.test/rss", type="rss", priority=1, category="official")

    def test_collection_counts_insert_duplicate_old_and_future_entries(self):
        transport = httpx.MockTransport(lambda request: httpx.Response(200, content=FIXTURE_BYTES))
        with httpx.Client(transport=transport) as client:
            first = collect_rss(self.source, "run-1", client=client, now=self.now)
            second = collect_rss(self.source, "run-2", client=client, now=self.now)
        self.assertTrue(first.healthy)
        self.assertEqual((first.entries_parsed, first.recent_entries, first.inserted), (4, 2, 2))
        self.assertEqual(second.duplicates, 2)

    def test_non_2xx_response_is_an_unhealthy_source(self):
        transport = httpx.MockTransport(lambda request: httpx.Response(404))
        with httpx.Client(transport=transport) as client:
            result = collect_rss(self.source, "run-1", client=client, now=self.now)
        self.assertFalse(result.healthy)
        self.assertEqual(result.error_category, "http_404")
```

Convert `test_organization.py` into a `unittest.TestCase` so discovery runs it.

- [ ] **Step 2: Run focused tests and confirm RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_rss_collector tests.test_organization -v
```

Expected: the existing collector returns a list, does not use the mock client, and does not implement freshness or health accounting.

- [ ] **Step 3: Implement explicit fetch and health results**

Add these constants to `rss_collector.py`:

```python
MAX_ITEM_AGE_DAYS = 7
MAX_FUTURE_SKEW_HOURS = 24
MAX_SNIPPET_CHARS = 1500
REQUEST_TIMEOUT_SECONDS = 20.0
USER_AGENT = "AI-Signal-Scout/1.0 (+https://github.com/True-Xman/AI-News-Agent)"
```

Fetch with `httpx.Client(follow_redirects=True, timeout=20.0, headers={"User-Agent": USER_AGENT})`, call `raise_for_status`, parse response bytes, and derive timestamps from `published_parsed` or `updated_parsed`. Missing links are skipped. Undated entries are accepted and counted. Old and future entries are skipped. Catch request and parse failures into stable categories without copying response bodies into logs or evidence.

Replace `sources.yaml` with the nine-endpoint table in the design. Extend organization mapping for Hugging Face and LangGraph. Keep source priority unique from 1 through 9.

- [ ] **Step 4: Verify collector behavior and live configuration parsing**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_rss_collector tests.test_organization -v
.\.venv\Scripts\python.exe -c "from src.config.config_loader import load_sources; s=load_sources(); assert len(s)==9; assert len({x.priority for x in s})==9"
```

Expected: deterministic fixture counts pass and all nine configured sources load with unique priorities.

- [ ] **Step 5: Commit source reliability changes**

```powershell
git add sources.yaml src/collectors/rss_collector.py src/config/config_loader.py src/utils/organization.py tests/fixtures/sample_feed.xml tests/test_rss_collector.py tests/test_organization.py
git commit -m "feat: add reliable source health collection"
```

---

### Task 4: Validated Sieve Batches

**Files:**
- Create: `src/intelligence/contracts.py`
- Create: `tests/test_sieve.py`
- Modify: `src/intelligence/sieve.py:1-108`
- Modify: `prompts/sieve_prompt.md:1-22`

**Interfaces:**
- Consumes: up to 50 balanced current-run raw rows and an async request callable.
- Produces: `SieveDecision`, `SieveResult(evaluated, kept, discarded)`, `parse_json_value(text, expected_type)`, and `run_sieve(run_id, request_fn=None) -> SieveResult`.
- Guarantees: exactly one validated decision for each candidate in every submitted batch.

- [ ] **Step 1: Write failing contract and Sieve tests**

```python
import asyncio
import hashlib
import json

from src.errors import ResponseValidationError
from src.intelligence.sieve import run_sieve
from src.storage.operations import insert_raw_signal
from tests.helpers import TemporaryDatabaseTestCase, make_raw_signal


class SieveTests(TemporaryDatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.hashes = []
        for index in range(2):
            signal = make_raw_signal(f"https://example.com/{index}", source=f"Source {index}", source_id=index + 1)
            insert_raw_signal(signal, "run-1")
            self.hashes.append(hashlib.md5(signal.url.encode()).hexdigest())

    def test_rejects_missing_and_unknown_hashes(self):
        async def incomplete_response(prompt):
            return '[{"url_hash":"unknown","decision":"KEEP","reason":"x","confidence":0.8,"scores":{}}]'
        with self.assertRaises(ResponseValidationError):
            asyncio.run(run_sieve("run-1", request_fn=incomplete_response))

    def test_updates_every_row_from_a_complete_batch(self):
        async def complete_response(prompt):
            return json.dumps([
                {"url_hash": self.hashes[0], "decision": "KEEP", "reason": "Material capability change", "confidence": 0.9, "scores": {"agent_relevance": 80}},
                {"url_hash": self.hashes[1], "decision": "DISCARD", "reason": "Minor update", "confidence": 0.8, "scores": {"agent_relevance": 20}},
            ])
        result = asyncio.run(run_sieve("run-1", request_fn=complete_response))
        self.assertEqual((result.evaluated, result.kept, result.discarded), (2, 1, 1))
```

Also test fenced JSON extraction, duplicate response hashes, invalid decisions, and confidence outside 0 through 1.

- [ ] **Step 2: Run focused tests and confirm RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_sieve -v
```

Expected: contract models are missing and current Sieve silently continues after incomplete responses.

- [ ] **Step 3: Implement strict response contracts**

```python
class SieveDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url_hash: str
    decision: Literal["KEEP", "DISCARD"]
    reason: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    scores: dict[str, float]


@dataclass(frozen=True)
class SieveResult:
    evaluated: int
    kept: int
    discarded: int
```

`parse_json_value` removes an optional Markdown fence, extracts the outer list or object, and raises `ResponseValidationError` on invalid JSON. `run_sieve` processes batches of five, compares response hashes exactly with request hashes, rejects duplicates and unknowns, updates every row with the active `run_id`, and propagates Gemini or validation failures.

Rewrite `sieve_prompt.md` to describe a JSON array, include `url_hash` in every decision, require one decision per input, and require English reasons.

- [ ] **Step 4: Verify Sieve behavior**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_sieve -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: complete batches update all rows and every malformed or incomplete response fails explicitly.

- [ ] **Step 5: Commit Sieve contracts**

```powershell
git add prompts/sieve_prompt.md src/intelligence/contracts.py src/intelligence/sieve.py tests/test_sieve.py
git commit -m "feat: validate complete Sieve batches"
```

---

### Task 5: Deterministic Scout Scoring and Diversity

**Files:**
- Create: `tests/test_scout.py`
- Modify: `src/intelligence/contracts.py`
- Modify: `src/intelligence/scout.py:1-109`
- Modify: `src/models/scored_signal.py:1-16`
- Modify: `prompts/scout_prompt.md:1-44`

**Interfaces:**
- Consumes: up to 15 balanced KEEP rows and an async request callable.
- Produces: `ScoreBreakdown`, `ScoutAnalysis`, `ScoutResult(analyzed, selected)`, `calculate_weighted_score(breakdown) -> float`, `select_diverse(signals: list[dict], limit=5, max_per_source=2) -> list[dict]`, and `run_scout(run_id, request_fn=None) -> ScoutResult`.

- [ ] **Step 1: Write failing scoring and diversity tests**

```python
import unittest

from src.intelligence.contracts import ScoreBreakdown
from src.intelligence.scout import calculate_weighted_score, select_diverse


class ScoutSelectionTests(unittest.TestCase):
    def test_weighted_score_is_computed_in_python(self):
        breakdown = ScoreBreakdown(
            capability_shift=100,
            real_world_impact=80,
            agent_relevance=60,
            x_discussion_potential=40,
            novelty=20,
            source_quality=100,
        )
        self.assertEqual(calculate_weighted_score(breakdown), 71.0)

    def test_two_pass_diversity_fills_five_slots(self):
        signals = [
            {"title": f"Signal {index}", "organization": organization, "score": 100 - index}
            for index, organization in enumerate(("OpenAI", "OpenAI", "OpenAI", "DeepMind", "OWASP", "arXiv"))
        ]
        selected = select_diverse(signals, limit=5, max_per_source=2)
        self.assertEqual(len(selected), 5)
        self.assertLessEqual(sum(s["organization"] == "OpenAI" for s in selected[:4]), 2)
```

Add async tests proving all supplied hashes are required, unknown hashes are rejected, source URLs are restored from storage rather than model output, and only five current-run rows are inserted.

- [ ] **Step 2: Run focused tests and confirm RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_scout -v
```

Expected: score models and pure selection functions do not exist; current Scout limits input to five and output to three.

- [ ] **Step 3: Implement structured analysis and deterministic ranking**

```python
class ScoreBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")
    capability_shift: float = Field(ge=0, le=100)
    real_world_impact: float = Field(ge=0, le=100)
    agent_relevance: float = Field(ge=0, le=100)
    x_discussion_potential: float = Field(ge=0, le=100)
    novelty: float = Field(ge=0, le=100)
    source_quality: float = Field(ge=0, le=100)


def calculate_weighted_score(scores: ScoreBreakdown) -> float:
    return round(
        scores.capability_shift * 0.25
        + scores.real_world_impact * 0.20
        + scores.agent_relevance * 0.20
        + scores.x_discussion_potential * 0.15
        + scores.novelty * 0.10
        + scores.source_quality * 0.10,
        1,
    )
```

Require `plain_english_explanation` and `x_discussion_angle` in `ScoutAnalysis`. Ask Gemini to analyze every input candidate, not select a Top 5. Validate exact hash coverage, restore source URLs and organizations from input mappings, compute scores in Python, rank by score/recency/hash, apply the two-pass diversity function, and insert only selected rows for the active run.

Rewrite `scout_prompt.md` entirely in English. Require evidence grounded only in title and snippet, explicit wording when details are insufficient, all six 0–100 criteria, and one output object per input candidate.

- [ ] **Step 4: Verify Scout scoring and selection**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_scout -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: the 25/20/20/15/10/10 calculation, deterministic ties, URL restoration, exact response coverage, diversity first pass, and five-slot fill all pass.

- [ ] **Step 5: Commit Scout behavior**

```powershell
git add prompts/scout_prompt.md src/intelligence/contracts.py src/intelligence/scout.py src/models/scored_signal.py tests/test_scout.py
git commit -m "feat: rank Scout results deterministically"
```

---

### Task 6: English Report and Safe Telegram Delivery

**Files:**
- Rewrite: `tests/test_formatter.py`
- Create: `tests/test_telegram.py`
- Modify: `src/reporting/formatter.py:1-91`
- Modify: `src/reporting/telegram.py:1-101`
- Modify: `src/models/daily_report.py:1-11`

**Interfaces:**
- Consumes: a list of validated Scout analysis dictionaries.
- Produces: `format_report(signals) -> str`, `validate_report(report, item_count) -> None`, `contains_arabic_script(text) -> bool`, and `TelegramClient.send_message(text, client=None) -> bool`.

- [ ] **Step 1: Replace Persian formatter tests with failing English contract tests**

```python
import unittest

from src.errors import ResponseValidationError
from src.reporting.formatter import format_report, validate_report


SAMPLE_SIGNAL = {
    "title": "Verified capability update",
    "score": 84.5,
    "what_happened": "The source announced a measured capability change.",
    "why_it_matters": "The change affects practical agent workflows.",
    "plain_english_explanation": "The tool can now complete a useful task more reliably.",
    "x_discussion_angle": "Discuss the measured impact and remaining limits.",
    "source_url": "https://example.com/verified-update",
}


class EnglishReportFormatterTests(unittest.TestCase):
    def test_report_uses_english_header_and_labels(self):
        report = format_report([SAMPLE_SIGNAL])
        self.assertTrue(report.startswith("AI Signal Scout\nDaily AI intelligence brief — 1 signal\n"))
        for label in ("Score:", "What happened:", "Why it matters:", "Plain-English explanation:", "X discussion angle:", "Source:"):
            self.assertIn(label, report)

    def test_report_rejects_arabic_script(self):
        with self.assertRaisesRegex(ResponseValidationError, "Arabic-script"):
            validate_report("گزارش", item_count=1)

    def test_report_limits_what_happened_to_three_lines(self):
        signal = {**SAMPLE_SIGNAL, "what_happened": "1\n2\n3\n4"}
        self.assertNotIn("\n4\n", format_report([signal]))
```

In `test_telegram.py`, use `httpx.MockTransport` to assert chunk lengths never exceed 4,096, a Telegram `{ "ok": false }` response returns `False`, and logs do not contain the configured channel or returned message ID.

- [ ] **Step 2: Run report and Telegram tests and confirm RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_formatter tests.test_telegram -v
```

Expected: `format_report`, the English fields, report validation, and injectable HTTP client are absent.

- [ ] **Step 3: Implement the English formatter and privacy-safe sender**

Use singular/plural headers based on item count. Use `Untitled signal`, `Not provided`, and `Source unavailable` as explicit English fallbacks. Format scores with one decimal. Preserve plain-text delivery.

```python
ARABIC_SCRIPT_PATTERN = re.compile(r"[\u0600-\u06ff]")


def contains_arabic_script(text: str) -> bool:
    return bool(ARABIC_SCRIPT_PATTERN.search(text))


def validate_report(report: str, item_count: int) -> None:
    if not 1 <= item_count <= 5:
        raise ResponseValidationError("Report item count must be between 1 and 5")
    if contains_arabic_script(report):
        raise ResponseValidationError("Report contains Arabic-script characters")
```

Allow `TelegramClient.send_message` to receive an existing `httpx.Client` for tests. Log chunk count and success only; remove message ID logging and Persian-specific comments.

- [ ] **Step 4: Verify the report boundary**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_formatter tests.test_telegram -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: English labels, Arabic-script rejection, fallbacks, truncation, chunking, and private-identifier log tests pass.

- [ ] **Step 5: Commit reporting changes**

```powershell
git add src/models/daily_report.py src/reporting/formatter.py src/reporting/telegram.py tests/test_formatter.py tests/test_telegram.py
git commit -m "feat: produce validated English reports"
```

---

### Task 7: Pipeline Outcomes and Sanitized Evidence

**Files:**
- Create: `src/evidence.py`
- Create: `src/pipeline.py`
- Create: `tests/test_evidence.py`
- Rewrite: `tests/test_main_pipeline.py`
- Modify: `src/main.py:1-110`
- Modify: `main.py:1-61`

**Interfaces:**
- Consumes: `PipelineDependencies(load_sources, collect_source, run_sieve, run_scout, get_report_signals, send_telegram)`; production defaults are selected only at runtime.
- Produces: `PipelineSummary` whose counters default to zero, `default_dependencies() -> PipelineDependencies`, `write_run_summary(summary, path) -> None`, `run_pipeline(deliver_report=True, summary_path="artifacts/run_summary.json", dependencies=None) -> PipelineSummary`, and CLI exit code 0 or 1.

- [ ] **Step 1: Write failing pipeline and evidence tests**

```python
import json
import tempfile
import unittest
from pathlib import Path

from src.collectors.rss_collector import SourceCollectionResult
from src.config.config_loader import SourceItem
from src.errors import ExternalServiceError
from src.evidence import PipelineSummary, write_run_summary
from src.intelligence.contracts import ScoutResult, SieveResult
from src.pipeline import PipelineDependencies, run_pipeline


class EvidenceTests(unittest.TestCase):
    def test_serialized_summary_contains_only_allowlisted_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "summary.json")
            summary = PipelineSummary(run_id="run-1", status="no_new_report", report_language="English")
            write_run_summary(summary, path)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["report_language"], "English")
            forbidden = {"report_text", "channel_id", "message_id", "article_snippets", "local_path"}
            self.assertTrue(forbidden.isdisjoint(payload))


def make_dependencies(report_signals=None, telegram_result=True):
    async def sieve(run_id):
        return SieveResult(evaluated=0, kept=0, discarded=0)

    async def scout(run_id):
        return ScoutResult(analyzed=0, selected=len(report_signals or []))

    return PipelineDependencies(
        load_sources=lambda: [SourceItem(name="Fixture", url="https://feed.test/rss", type="rss", priority=1, category="official")],
        collect_source=lambda source, run_id: SourceCollectionResult(source_name=source.name, healthy=True),
        run_sieve=sieve,
        run_scout=scout,
        get_report_signals=lambda run_id, limit: list(report_signals or []),
        send_telegram=lambda report: telegram_result,
    )


class PipelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_new_signals_succeeds_without_delivery(self):
        summary = await run_pipeline(deliver_report=True, dependencies=make_dependencies())
        self.assertEqual(summary.status, "no_new_report")
        self.assertFalse(summary.delivery_attempted)

    async def test_requested_delivery_failure_raises(self):
        valid_signal = {
            "title": "Verified signal",
            "score": 80.0,
            "what_happened": "A documented capability changed.",
            "why_it_matters": "The change affects agent workflows.",
            "plain_english_explanation": "The tool can now complete a useful task.",
            "x_discussion_angle": "Discuss the measured workflow impact.",
            "source_url": "https://example.com/signal",
        }
        with self.assertRaises(ExternalServiceError):
            await run_pipeline(deliver_report=True, dependencies=make_dependencies([valid_signal], telegram_result=False))
```

Add tests for source health below 60 percent, malformed Gemini propagation, current-run-only report count, `STATE_RESTORED` parsing, and summary creation on expected failures.

- [ ] **Step 2: Run pipeline tests and confirm RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_evidence tests.test_main_pipeline -v
```

Expected: evidence and dependency-injected pipeline modules do not exist; current `src.main` returns successfully after failures.

- [ ] **Step 3: Implement orchestration with explicit outcomes**

Define Pydantic evidence models with `extra="forbid"`. Per-source evidence contains only source name, healthy flag, and counts/error category. Read `STATE_RESTORED` using a strict case-insensitive `true` comparison.

`run_pipeline` performs these stages in order:

```text
initialize counts -> collect -> enforce source threshold -> Sieve -> Scout
-> query active run -> format/validate English -> optional delivery
-> final counts -> write sanitized summary -> return
```

On `PipelineError`, set status `failed`, include only the exception class as `failure_category`, write the summary, and re-raise. On zero report items, set `no_new_report`, skip Telegram, write the summary, and return successfully.

`src/main.py` parses `--deliver-report true|false`, loads `.env` only for local execution, invokes the pipeline, and exits 1 for `PipelineError` or unexpected exceptions. Replace root `main.py` with a thin wrapper that calls the same CLI entry point.

- [ ] **Step 4: Verify orchestration and sanitized serialization**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_evidence tests.test_main_pipeline -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: normal no-news outcomes are successful, operational failures are nonzero-capable exceptions, and serialized evidence contains only allowlisted fields.

- [ ] **Step 5: Commit orchestration and evidence**

```powershell
git add main.py src/evidence.py src/main.py src/pipeline.py tests/test_evidence.py tests/test_main_pipeline.py
git commit -m "feat: record explicit pipeline outcomes"
```

---

### Task 8: Honest Offline and Source Validation Commands

**Files:**
- Delete: `e2e_validation.py`
- Create: `scripts/check_sources.py`
- Create: `scripts/validate_offline.py`
- Create: `tests/test_validation_scripts.py`

**Interfaces:**
- Produces: `python scripts/check_sources.py`, a live RSS-only health command with no API keys.
- Produces: `python scripts/validate_offline.py`, a fixture-driven integration command that contacts no external service.

- [ ] **Step 1: Write failing validation-script tests**

```python
import subprocess
import sys
import unittest


class ValidationScriptTests(unittest.TestCase):
    def test_offline_validation_identifies_itself_as_simulated(self):
        result = subprocess.run(
            [sys.executable, "scripts/validate_offline.py"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OFFLINE INTEGRATION VALIDATION", result.stdout)
        self.assertIn("No external Gemini or Telegram service was contacted", result.stdout)

    def test_source_check_help_requires_no_credentials(self):
        result = subprocess.run([sys.executable, "scripts/check_sources.py", "--help"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
```

- [ ] **Step 2: Run validation-script tests and confirm RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_validation_scripts -v
```

Expected: the new commands are missing and the existing script is misleadingly named end-to-end.

- [ ] **Step 3: Implement both commands with explicit boundaries**

`validate_offline.py` uses `TemporaryDirectory`, the sample RSS fixture, deterministic async Sieve/Scout response functions, and a recording Telegram adapter. It asserts the final summary is English, contains one through five items, and has no delivery attempt. Its first and last output lines state the offline/simulated boundary.

`check_sources.py` loads all nine sources, calls the same collector fetch/parse path in a temporary database, prints columns `Source`, `Healthy`, `Parsed`, `Recent`, and `Error category`, and returns 1 when fewer than 60 percent are healthy.

- [ ] **Step 4: Verify offline integration and command tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_validation_scripts -v
.\.venv\Scripts\python.exe scripts/validate_offline.py
```

Expected: tests pass; offline validation prints the non-live disclaimer and completes without credentials or network access.

- [ ] **Step 5: Commit validation boundary changes**

```powershell
git add e2e_validation.py scripts/check_sources.py scripts/validate_offline.py tests/test_validation_scripts.py
git commit -m "test: separate offline and live validation"
```

---

### Task 9: Cache-Persistent GitHub Actions Workflow

**Files:**
- Create: `tests/test_workflow.py`
- Modify: `.github/workflows/daily_agent.yml:1-37`

**Interfaces:**
- Consumes: repository secrets `GOOGLE_API_KEY`, `TELEGRAM_BOT_TOKEN`, and `TELEGRAM_CHANNEL_ID`.
- Produces: scheduled delivery runs, manual `deliver_report` runs, branch-scoped SQLite restore/save, serialized same-ref execution, and run-specific sanitized artifacts.

- [ ] **Step 1: Write a failing static workflow-contract test**

```python
import unittest
from pathlib import Path


class WorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = Path(".github/workflows/daily_agent.yml").read_text(encoding="utf-8")

    def test_workflow_has_persistence_and_evidence_steps(self):
        for required in (
            "actions/cache/restore@v6",
            "actions/cache/save@v6",
            "data/signals.db",
            "actions/upload-artifact@v7",
            "artifacts/run_summary.json",
            "deliver_report:",
            "concurrency:",
            "python -m unittest discover -s tests -v",
        ):
            self.assertIn(required, self.text)

    def test_tests_run_before_live_pipeline(self):
        self.assertLess(self.text.index("python -m unittest"), self.text.index("python -m src.main"))
```

Also assert `permissions: contents: read`, `timeout-minutes: 15`, current `actions/checkout@v7` and `actions/setup-python@v7`, and a success-only condition on the cache-save step.

- [ ] **Step 2: Run workflow tests and confirm RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_workflow -v
```

Expected: the current workflow has no cache, tests, input, concurrency, timeout, or artifact.

- [ ] **Step 3: Implement the workflow contract**

Use this job order:

```yaml
permissions:
  contents: read

concurrency:
  group: ai-signal-scout-${{ github.ref }}
  cancel-in-progress: false

jobs:
  run-agent:
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: "3.11"
          cache: pip
      - run: python -m pip install -r requirements.txt
      - run: python -m unittest discover -s tests -v
      - id: restore-db
        uses: actions/cache/restore@v6
        with:
          path: data/signals.db
          key: ai-signal-scout-db-${{ runner.os }}-${{ github.ref_name }}-${{ github.run_id }}
          restore-keys: ai-signal-scout-db-${{ runner.os }}-${{ github.ref_name }}-
      - run: python -m src.main --deliver-report "${{ github.event_name == 'schedule' || inputs.deliver_report }}"
      - if: always()
        uses: actions/upload-artifact@v7
        with:
          name: signal-scout-evidence-${{ github.run_id }}
          path: artifacts/run_summary.json
          if-no-files-found: error
      - if: success()
        uses: actions/cache/save@v6
        with:
          path: data/signals.db
          key: ai-signal-scout-db-${{ runner.os }}-${{ github.ref_name }}-${{ github.run_id }}
```

Set `STATE_RESTORED` from whether `steps.restore-db.outputs.cache-matched-key` is nonempty. Define `workflow_dispatch.inputs.deliver_report` as a boolean defaulting to `false`; scheduled events override it to true. Keep credentials only in the live pipeline step environment.

- [ ] **Step 4: Verify workflow ordering and all tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_workflow -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: the static workflow contract and all unit tests pass.

- [ ] **Step 5: Commit workflow persistence**

```powershell
git add .github/workflows/daily_agent.yml tests/test_workflow.py
git commit -m "ci: persist state and publish run evidence"
```

---

### Task 10: Truthful Documentation, Public Safety, and Final Live Evidence

**Files:**
- Create: `.env.example`
- Create: `tests/test_public_contract.py`
- Modify: `.gitignore:1-18`
- Rewrite: `README.md`
- Rewrite: `docs/architecture.md`
- Rewrite: `docs/decisions.md`

**Interfaces:**
- Consumes: the implemented behavior and verified commands from Tasks 1–9.
- Produces: public documentation matching runtime truth, repository-language guards, two live run artifacts, and a prepared pull request.

- [ ] **Step 1: Write failing public-contract tests**

```python
import re
import unittest
from pathlib import Path


class PublicContractTests(unittest.TestCase):
    def test_professional_path_contains_no_arabic_script(self):
        paths = [Path("src"), Path("prompts"), Path("README.md"), Path("docs/architecture.md"), Path("docs/decisions.md")]
        offenders = []
        for path in paths:
            files = [path] if path.is_file() else list(path.rglob("*.py")) + list(path.rglob("*.md"))
            for file in files:
                if re.search(r"[\u0600-\u06ff]", file.read_text(encoding="utf-8")):
                    offenders.append(str(file))
        self.assertEqual(offenders, [])

    def test_readme_uses_qualified_portfolio_language(self):
        readme = Path("README.md").read_text(encoding="utf-8")
        self.assertIn("up to five", readme.lower())
        self.assertIn("cache", readme.lower())
        self.assertIn("offline integration", readme.lower())
        self.assertNotIn("production-grade", readme.lower())
        self.assertNotIn("enterprise-ready", readme.lower())
```

Add assertions that `.env.example` contains all three variable names but no token-shaped values, and that architecture does not call the collector stubbed or claim a reports table.

- [ ] **Step 2: Run public-contract tests and confirm RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_public_contract -v
```

Expected: Persian text and inaccurate claims remain; `.env.example` is absent.

- [ ] **Step 3: Rewrite documentation to match verified behavior**

README sections must be: purpose, architecture, source set, selection contract, automation, persistence and cache limitation, required environment names, local commands, verification levels, sanitized evidence, known limitations, and safe portfolio claims.

Update `docs/architecture.md` with the actual packages and current-run flow. Update `docs/decisions.md` with accepted decisions for two-stage Gemini analysis, deterministic Python scoring, cache-backed SQLite state, RSS-only sources, Telegram, Actions evidence, and explicit limitations.

Use nonfunctional values only:

```dotenv
GOOGLE_API_KEY=replace-with-a-local-gemini-key
TELEGRAM_BOT_TOKEN=replace-with-a-local-bot-token
TELEGRAM_CHANNEL_ID=replace-with-a-local-channel-id
```

Ignore `.env.*` while explicitly allowing `.env.example`. Do not add report samples containing private Telegram output.

- [ ] **Step 4: Run complete local verification before the documentation commit**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/validate_offline.py
.\.venv\Scripts\python.exe scripts/check_sources.py
rg -n "[\u0600-\u06FF]" src prompts README.md docs/architecture.md docs/decisions.md
git diff --check
git status --short
```

Expected: tests and both validations pass; the Arabic-script scan returns no matches; diff check is clean; only intended files are modified.

- [ ] **Step 5: Run redacted current-tree and history secret scans**

Scan tracked content and all revisions for Google API key, Telegram bot token, private key, and numeric Telegram channel patterns. Output file paths and pattern categories only, never matched values. Confirm `.env`, databases, evidence output, and virtual environments are untracked.

Expected: no credential-shaped match. Nonfunctional examples may be reviewed manually and must not match live-token regexes.

- [ ] **Step 6: Commit truthful documentation**

```powershell
git add .env.example .gitignore README.md docs/architecture.md docs/decisions.md tests/test_public_contract.py
git commit -m "docs: align public claims with verified behavior"
```

- [ ] **Step 7: Perform the pre-push verification gate**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/validate_offline.py
.\.venv\Scripts\python.exe scripts/check_sources.py
git diff --check origin/main...HEAD
git status --short --branch
git log --oneline origin/main..HEAD
```

Expected: all commands pass, the worktree is clean, and commit history is logically separated.

- [ ] **Step 8: Push the feature branch**

```powershell
git push --set-upstream origin codex/portfolio-hardening
```

Expected: the remote branch points to local HEAD.

- [ ] **Step 9: Dispatch and verify the live English delivery run**

Use an authenticated GitHub REST request to dispatch `.github/workflows/daily_agent.yml` at ref `codex/portfolio-hardening` with:

```json
{"ref":"codex/portfolio-hardening","inputs":{"deliver_report":"true"}}
```

Wait for the new run to complete. Verify conclusion `success`, download the run-specific evidence artifact through the authenticated API, and assert:

```text
report_language = English
status = delivered
report_signal_count is between 1 and 5
delivery_requested = true
delivery_succeeded = true
```

Inspect the artifact keys to confirm no forbidden fields are present. Record the Actions run and artifact URLs.

- [ ] **Step 10: Dispatch and verify the cross-run persistence run**

Dispatch the same ref with:

```json
{"ref":"codex/portfolio-hardening","inputs":{"deliver_report":"false"}}
```

Verify a distinct successful run whose evidence states:

```text
state_restored = true
duplicates_skipped > 0
delivery_requested = false
```

If new feed items produce a report, ensure it remains English; no Telegram call occurs in this run.

- [ ] **Step 11: Prepare the pull request without merging**

Create a PR from `codex/portfolio-hardening` to `main` titled:

```text
Harden AI Signal Scout as verified portfolio evidence
```

The PR body must summarize English output, cache-backed deduplication, source repairs, deterministic up-to-five ranking, validation boundaries, sanitized artifacts, both live run links, security scan results, and known cache/RSS/model limitations. Do not claim indefinite persistence or comprehensive end-to-end coverage. Leave the PR unmerged.

- [ ] **Step 12: Produce the portfolio evidence bundle**

Return the requested `AI SIGNAL SCOUT — PORTFOLIO EVIDENCE BUNDLE`, including architecture, automation, user-directed decisions, discovered bugs, fixes, verification, runtime links, limitations, safe/qualified/unsupported claims, recommended status, LinkedIn evidence assets, next action, cross-project impact, and whether `SOURCE UPDATE REQUIRED` applies.

State separately that existing history contains a personal email and that no history rewrite was performed. Recommend a merge only after the user reviews the PR and explicitly authorizes it.
