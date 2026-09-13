import re
import unittest
from pathlib import Path


class PublicContractTests(unittest.TestCase):
    def test_professional_path_contains_no_arabic_script(self):
        paths = [
            Path("src"),
            Path("prompts"),
            Path("README.md"),
            Path("docs/architecture.md"),
            Path("docs/decisions.md"),
        ]
        offenders = []
        for path in paths:
            files = (
                [path]
                if path.is_file()
                else list(path.rglob("*.py")) + list(path.rglob("*.md"))
            )
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

    def test_environment_example_is_nonfunctional(self):
        example = Path(".env.example").read_text(encoding="utf-8")
        for name in (
            "GOOGLE_API_KEY",
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_CHANNEL_ID",
        ):
            self.assertIn(f"{name}=", example)
        self.assertNotRegex(example, r"AIza[0-9A-Za-z_-]{20,}")
        self.assertNotRegex(example, r"\d{6,}:[0-9A-Za-z_-]{20,}")

    def test_architecture_matches_implemented_storage(self):
        architecture = Path("docs/architecture.md").read_text(encoding="utf-8").lower()
        self.assertNotIn("currently stubbed", architecture)
        self.assertNotIn("reports table", architecture)
        self.assertIn("raw_signals", architecture)
        self.assertIn("processed_signals", architecture)

    def test_environment_ignore_rules_allow_only_the_example(self):
        ignore = Path(".gitignore").read_text(encoding="utf-8")
        self.assertIn(".env.*", ignore)
        self.assertIn("!.env.example", ignore)


if __name__ == "__main__":
    unittest.main()
