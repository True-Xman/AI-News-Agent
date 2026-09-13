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


if __name__ == "__main__":
    unittest.main()
