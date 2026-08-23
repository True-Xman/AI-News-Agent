import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.organization import get_organization

def test_get_organization():
    
    # Test cases
    assert get_organization("https://deepmind.google/blog/feed", "DeepMind Blog") == "Google DeepMind"
    assert get_organization("https://techcrunch.com/some/article", "TechCrunch") == "TechCrunch"
    assert get_organization("https://openai.com/blog", "OpenAI") == "OpenAI"
    # Test fallback
    assert get_organization(None, "OpenAI News") == "OpenAI"
    assert get_organization("https://unknown.com", "Unknown Org") == "Unknown Org"
    
    print("All tests passed!")

if __name__ == "__main__":
    test_get_organization()
