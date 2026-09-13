from urllib.parse import urlparse

def get_organization(url: str, fallback: str) -> str:
    """Infer organization name from URL domain."""
    
    # Define mapping
    org_map = {
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "deepmind": "Google DeepMind",
        "google": "Google DeepMind",
        "meta": "Meta",
        "facebook": "Meta",
        "arxiv": "arXiv",
        "techcrunch": "TechCrunch",
        "theverge": "The Verge",
        "langchain": "LangChain",
        "langgraph": "LangGraph",
        "huggingface": "Hugging Face",
        "owasp": "OWASP",
    }

    # 1. URL/domain matching
    if url:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain == "github.com" and "/langchain-ai/langgraph" in parsed.path.lower():
                return "LangGraph"
            for key, name in org_map.items():
                if key in domain:
                    return name
        except (TypeError, ValueError):
            pass
    
    # 2. Check fallback strings for patterns
    if fallback:
        fb_lower = fallback.lower()
        for key, name in org_map.items():
            if key in fb_lower:
                return name
                
    return fallback

