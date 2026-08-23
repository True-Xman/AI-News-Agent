import json
import logging
from .gemini_client import send_gemini_request
from ..utils.organization import get_organization
from ..storage.operations import get_unprocessed_raw_signals, update_signal_filter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with open("prompts/sieve_prompt.md", "r", encoding="utf-8") as f:
    SIEVE_PROMPT_TEMPLATE = f.read()

async def run_sieve(run_id: str):
    rows = get_unprocessed_raw_signals(run_id=run_id, limit=50) # Increase pull size to allow better selection diversity
    # Debug log: check distribution
    from collections import Counter
    source_counts = Counter([get_organization(None, row[2]) for row in rows])
    logger.info(f"Sieve: Raw signals loaded: {len(rows)}. Distribution: {dict(source_counts)}")
    for org, count in source_counts.items():
        sample = [row[1] for row in rows if get_organization(None, row[2]) == org][:2]
        logger.info(f"Sieve: Sample from {org}: {sample}")

    if not rows:
        return False # Indicate failure/stop

    # Pre-filter logic: Keep only relevant signals based on title keywords
    keywords = ["AI", "agent", "security", "model", "research", "LLM", "safety", "vulnerability"]
    filtered_rows = []
    for row in rows:
        title = row[1]
        if any(kw.lower() in title.lower() for kw in keywords):
            filtered_rows.append(row)
    
    if not filtered_rows:
        return True # Finished, but nothing to keep

    logger.info(f"Sieve: Candidates before diversity selection: {len(filtered_rows)}")

    # Group filtered candidates by detected source/organization to distribute and select a diverse subset
    # Detailed Logging
    for i, row in enumerate(filtered_rows):
        # Assuming row structure based on insert_raw_signal:
        # 0: url_hash, 1: title, 2: source, 3: source_id, 4: found_at, 5: snippet
        # But wait, raw_signals table has more columns...
        # Let's check the schema again. 
        # Column count: url_hash (0), title (1), source (2), source_id (3), found_at (4), snippet (5)
        # Yes, row[0] is hash, row[1] is title, row[2] is source
        
        # Actually, let's log everything
        logger.info(f"Signal {i}: Title: {row[1]}, Source: {row[2]}, URL Hash: {row[0]}")
    

    by_source = {}
    for row in filtered_rows:
        # row[0] is url_hash, row[1] is title, row[2] is raw source description
        # We don't store full URL in raw_signals table, so we pass fallback (row[2]) to get_organization
        source_org = get_organization(None, row[2] or "unknown")
        by_source.setdefault(source_org, []).append(row)

    # Round-robin selection of candidates to ensure high diversity up to a maximum of 25 candidates
    selected_rows = []
    sources_cycle = list(by_source.keys())
    while len(selected_rows) < 25 and any(by_source.values()):
        for src in list(sources_cycle):
            if by_source[src]:
                selected_rows.append(by_source[src].pop(0))
            else:
                sources_cycle.remove(src)
            if len(selected_rows) >= 25:
                break

    represented_orgs = {get_organization(None, row[2] or "unknown") for row in selected_rows}
    logger.info(f"Sieve: Final candidates sent to Sieve (Gemini): {len(selected_rows)}. Organizations represented: {represented_orgs}")


    # Batch process signals (e.g., 5 at a time)
    batch_size = 5
    for i in range(0, len(selected_rows), batch_size):
        batch = selected_rows[i:i + batch_size]
        
        candidates = []
        for row in batch:
            url_hash, title, source, source_id, found_at, snippet = row[:6]
            candidates.append({
                "url_hash": url_hash,
                "title": title,
                "source": source,
                "snippet": snippet or ""
            })
        
        prompt = f"{SIEVE_PROMPT_TEMPLATE}\n\nEvaluate these candidates and return a JSON list of decisions:\n{json.dumps(candidates)}"
        
        try:
            response_text = await send_gemini_request(prompt)
            # Find JSON in response
            start = response_text.find("[")
            end = response_text.rfind("]") + 1
            if start == -1 or end == 0:
                logger.error("Failed to find JSON array in response")
                continue
                
            data = json.loads(response_text[start:end])
            
            for item in data:
                url_hash = item.get("url_hash")
                decision = item.get("decision")
                if decision in ["KEEP", "DISCARD"]:
                    update_signal_filter(
                        url_hash, 
                        decision, 
                        item.get("reason", ""), 
                        item.get("confidence", 0.0),
                        item.get("scores"),
                        run_id=run_id
                    )
        except Exception as e:
            if "quota" in str(e).lower() or "exceeded" in str(e).lower():
                logger.error("Sieve stopped due to Gemini quota exhaustion.")
                return False
            logger.error(f"Error sieving batch starting with {batch[0][1]}: {e}")
    return True

