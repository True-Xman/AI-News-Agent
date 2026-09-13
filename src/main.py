"""Command-line entry point for the AI Signal Scout pipeline."""

import argparse
import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

from .errors import PipelineError
from .pipeline import run_pipeline


logger = logging.getLogger("AI-Signal-Scout")


def _boolean_argument(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise argparse.ArgumentTypeError("expected true or false")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the AI Signal Scout pipeline")
    parser.add_argument(
        "--deliver-report",
        type=_boolean_argument,
        default=True,
        metavar="true|false",
        help="send a valid current-run report to Telegram (default: true)",
    )
    parser.add_argument(
        "--summary-path",
        default="artifacts/run_summary.json",
        help="write sanitized run evidence to this path",
    )
    return parser


def cli(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    if os.environ.get("GITHUB_ACTIONS", "").lower() != "true":
        load_dotenv()

    args = build_parser().parse_args(argv)
    try:
        summary = asyncio.run(
            run_pipeline(
                deliver_report=args.deliver_report,
                summary_path=args.summary_path,
            )
        )
    except PipelineError as exc:
        logger.error("Pipeline failed: %s", type(exc).__name__)
        return 1
    except Exception as exc:
        logger.error("Unexpected pipeline failure: %s", type(exc).__name__)
        return 1

    logger.info("Pipeline completed with status %s", summary.status)
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
