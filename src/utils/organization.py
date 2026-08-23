from urllib.parse import urlparse

def get_organization(url: str, fallback: str) -> str:
    """Infer organization name from URL domain."""
    if not url:
        return fallback
    try:
        domain = urlparse(url).netloc.lower()
        if "openai" in domain: return "OpenAI"
        if "anthropic" in domain: return "Anthropic"
        if "deepmind" in domain or "google" in domain: return "Google DeepMind"
        if "meta" in domain or "facebook" in domain: return "Meta"
        if "arxiv" in domain: return "arXiv"
        if "techcrunch" in domain: return "TechCrunch"
        if "theverge" in domain: return "The Verge"
        if "langchain" in domain: return "LangChain"
    except:
        pass
    
    # Check fallback strings for patterns
    fb_lower = fallback.lower()
    if "openai" in fb_lower: return "OpenAI"
    if "anthropic" in fb_lower: return "Anthropic"
    if "deepmind" in fb_lower or "google" in fb_lower: return "Google DeepMind"
    if "meta" in fb_lower or "facebook" in fb_lower: return "Meta"
    if "arxiv" in fb_lower: return "arXiv"
    if "techcrunch" in fb_lower: return "TechCrunch"
    if "theverge" in fb_lower: return "The Verge"
    if "langchain" in fb_lower: return "LangChain"
    if "owasp" in fb_lower: return "OWASP"
    
    return fallback
