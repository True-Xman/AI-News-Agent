"""Live, credential-free health check for configured RSS and Atom sources."""

import argparse
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.collectors.rss_collector import collect_rss
from src.config.config_loader import load_sources
from src.storage.database import init_db


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a live RSS source health check without API credentials"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.60,
        help="minimum healthy-source ratio required for success (default: 0.60)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 0 <= args.threshold <= 1:
        print("Threshold must be between 0 and 1", file=sys.stderr)
        return 2

    sources = load_sources(PROJECT_ROOT / "sources.yaml")
    results = []
    with tempfile.TemporaryDirectory() as directory:
        previous_db_path = os.environ.get("SIGNALS_DB_PATH")
        os.environ["SIGNALS_DB_PATH"] = str(Path(directory, "source-health.db"))
        try:
            init_db()
            run_id = f"source-health-{uuid.uuid4()}"
            now = datetime.now(timezone.utc)
            with httpx.Client() as client:
                for source in sources:
                    results.append(
                        collect_rss(source, run_id, client=client, now=now)
                    )
        finally:
            if previous_db_path is None:
                os.environ.pop("SIGNALS_DB_PATH", None)
            else:
                os.environ["SIGNALS_DB_PATH"] = previous_db_path

    print(f"{'Source':<28} {'Healthy':<8} {'Parsed':>6} {'Recent':>6}  Error category")
    print("-" * 72)
    for result in results:
        print(
            f"{result.source_name[:28]:<28} "
            f"{str(result.healthy):<8} "
            f"{result.entries_parsed:>6} "
            f"{result.recent_entries:>6}  "
            f"{result.error_category or '-'}"
        )

    healthy = sum(result.healthy for result in results)
    ratio = healthy / len(results) if results else 0
    print(f"Healthy sources: {healthy}/{len(results)} ({ratio:.0%}); required: {args.threshold:.0%}")
    return 0 if ratio >= args.threshold else 1


if __name__ == "__main__":
    raise SystemExit(main())
