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
        "owasp": "OWASP"
    }

    # 1. URL/domain matching
    if url:
        try:
            domain = urlparse(url).netloc.lower()
            for key, name in org_map.items():
                if key in domain:
                    return name
        except:
            pass
    
    # 2. Check fallback strings for patterns
    if fallback:
        fb_lower = fallback.lower()
        for key, name in org_map.items():
            if key in fb_lower:
                return name
                
    # 3. Last ditch effort: Try splitting by hyphen if fallback contains it
    if fallback and "-" in fallback:
        parts = fallback.split("-")
        for part in parts:
            p_lower = part.strip().lower()
            for key, name in org_map.items():
                if key == p_lower:
                    return name
                
    return fallback

