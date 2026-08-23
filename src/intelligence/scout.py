import json
import logging
from .gemini_client import send_gemini_request
from ..utils.organization import get_organization
from ..storage.operations import get_keep_signals, insert_processed_signal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with open("prompts/scout_prompt.md", "r", encoding="utf-8") as f:
    SCOUT_PROMPT_TEMPLATE = f.read()

async def run_scout():
    rows = get_keep_signals()
    if not rows:
        return
    
    total_candidates = len(rows)
    # Enforce hard limit of 5, prefer top 3 if possible
    # We will limit the input candidates sent to Gemini to 5
    limited_rows = rows[:5]
    
    logger.info(f"Scout: Processing {total_candidates} candidates, sending {len(limited_rows)} to Gemini.")
    
    candidates = []
    # Create a mapping of url_hash to original data to ensure preservation
    hash_to_original = {}
    
    for row in limited_rows:
        # row structure: url_hash(0), title(1), source(2), source_id(3), found_at(4), 
        # snippet(5), ..., url(11)
        url_hash = row[0]
        original_url = row[11] if len(row) > 11 else f"https://news-scout.ai/signal/{url_hash}"
        
        hash_to_original[url_hash] = {
            "source_url": original_url,
            "source": row[2]
        }
        
        candidates.append({
            "url_hash": url_hash,
            "title": row[1],
            "source": row[2],
            "summary": row[5],
            "source_url": original_url
        })
    
    prompt = SCOUT_PROMPT_TEMPLATE + "\n\nCandidates:\n" + json.dumps(candidates)
    
    try:
        response_text = await send_gemini_request(prompt)
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        data = json.loads(response_text[start:end])
        
        # Sort and apply diversity filtering
        all_signals = data.get("selected_signals", [])
        
        # Validate and restore original URLs/Orgs if Gemini hallucinated or used placeholders
        for sig in all_signals:
            u_hash = sig.get("url_hash")
            if u_hash in hash_to_original:
                sig["source_url"] = hash_to_original[u_hash]["source_url"]
                # Keep the Gemini-detected org if it's better, but we have original source too
        logger.info(f"Scout: Candidates before diversity filtering: {len(all_signals)}")
        
        # Sort by raw score
        ranked_signals = sorted(data.get("selected_signals", []), key=lambda x: x.get("score", 0), reverse=True)
        
        # Diversity-aware selection strategy
        top_signals = []
        selected_sources = {} # source_name: count
        
        for sig in ranked_signals:
            if len(top_signals) >= 3:
                break
                
            source = get_organization(sig.get("source_url"), sig.get("source", "unknown"))
            raw_score = sig.get("score", 0)
            
            logger.info(f"Scout: Analyzing '{sig.get('title')}' - Detected Org: {source}")
            # Condition 1: New source
            # Condition 2: Repeated source only if it's significantly higher (>15 points) than the last added signal
            #              or if we are desperate to fill slots (not reached 3 signals) and no other unique source left.
            
            is_new_source = source not in selected_sources
            
            # Logic: allow repeat if score is significantly better than any previously selected signal
            # Or if it's the first time we see this source
            if is_new_source:
                top_signals.append(sig)
                selected_sources[source] = selected_sources.get(source, 0) + 1
                logger.info(f"Scout: Selected '{sig.get('title')}' from new source '{source}'")
            else:
                # Check if this signal is "significantly higher" (e.g., > 15 points) than the last selected signal
                # to justify picking it over another unique source.
                if len(top_signals) > 0 and raw_score > (top_signals[-1].get("score", 0) + 15):
                    top_signals.append(sig)
                    selected_sources[source] = selected_sources.get(source, 0) + 1
                    logger.info(f"Scout: Selected duplicate source '{source}' for '{sig.get('title')}' due to significantly higher score.")
                else:
                    logger.info(f"Scout: Skipping '{sig.get('title')}' (source '{source}') to maintain diversity.")

        # Final insertion logic using the adjusted strategy
        for signal in top_signals:
            insert_processed_signal(
                title=signal["title"],
                url=signal["source_url"],
                score=signal["score"],
                topic_fingerprint=signal["title"],
                analysis_json=signal
            )
    except Exception as e:
        logger.error(f"Error scouting: {e}")

