import unittest

from src.utils.organization import get_organization


class OrganizationTests(unittest.TestCase):
    def test_known_domains_and_fallbacks_are_normalized(self):
        cases = [
            (
                "https://deepmind.google/blog/feed",
                "DeepMind Blog",
                "Google DeepMind",
            ),
            ("https://techcrunch.com/some/article", "TechCrunch", "TechCrunch"),
            ("https://openai.com/blog", "OpenAI", "OpenAI"),
            (None, "OpenAI News", "OpenAI"),
            ("https://huggingface.co/blog", "HF Blog", "Hugging Face"),
            (
                "https://github.com/langchain-ai/langgraph/releases",
                "LangGraph releases",
                "LangGraph",
            ),
            ("https://unknown.com", "Unknown Org", "Unknown Org"),
        ]

        for url, fallback, expected in cases:
            with self.subTest(url=url, fallback=fallback):
                self.assertEqual(get_organization(url, fallback), expected)


if __name__ == "__main__":
    unittest.main()
