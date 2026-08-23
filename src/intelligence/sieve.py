import json
import logging
from .gemini_client import send_gemini_request
from ..utils.organization import get_organization
from ..storage.operations import get_unprocessed_raw_signals, update_signal_filter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with open("prompts/sieve_prompt.md", "r") as f:
    SIEVE_PROMPT_TEMPLATE = f.read()

async def run_sieve():
    rows = get_unprocessed_raw_signals(50) # Increase pull size to allow better selection diversity
    if not rows:
        return

    # Pre-filter logic: Keep only relevant signals based on title keywords
    keywords = ["AI", "agent", "security", "model", "research", "LLM", "safety", "vulnerability"]
    filtered_rows = []
    for row in rows:
        title = row[1]
        if any(kw.lower() in title.lower() for kw in keywords):
            filtered_rows.append(row)
    
    if not filtered_rows:
        return

    logger.info(f"Sieve: Candidates before diversity selection: {len(filtered_rows)}")

    # Group filtered candidates by detected source/organization to distribute and select a diverse subset
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
                        item.get("scores")
                    )
        except Exception as e:
            logger.error(f"Error sieving batch starting with {batch[0][1]}: {e}")

