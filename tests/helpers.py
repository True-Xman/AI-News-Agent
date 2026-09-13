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
        self.env = patch.dict(
            os.environ,
            {"SIGNALS_DB_PATH": os.path.join(self.tempdir.name, "signals.db")},
        )
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
        found_at=found_at if found_at is not None else time.time(),
        snippet="Evidence-backed summary",
    )
