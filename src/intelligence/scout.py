import json
import logging
from .gemini_client import send_gemini_request
from ..storage.operations import get_keep_signals, insert_processed_signal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with open("prompts/scout_prompt.md", "r") as f:
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
    for row in limited_rows:
        candidates.append({
            "url_hash": row[0],
            "title": row[1],
            "source": row[2],
            "summary": row[5]
        })
    
    prompt = SCOUT_PROMPT_TEMPLATE + "\n\nCandidates:\n" + json.dumps(candidates)
    
    try:
        response_text = await send_gemini_request(prompt)
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        data = json.loads(response_text[start:end])
        
        # Sort and apply diversity filtering
        all_signals = data.get("selected_signals", [])
        logger.info(f"Scout: Candidates before diversity filtering: {len(all_signals)}")
        
        # Diversity Penalty: Reduce score for subsequent items from the same source
        # Sort initially by raw score
        ranked_signals = sorted(all_signals, key=lambda x: x.get("score", 0), reverse=True)
        
        diversity_adjusted_signals = []
        seen_sources = {}
        
        for sig in ranked_signals:
            source = sig.get("source", "unknown")
            raw_score = sig.get("score", 0)
            
            # Diversity Penalty: Apply only if score > 70 (high impact threshold)
            # Reduce penalty to 10% incremental
            if raw_score > 70:
                penalty = seen_sources.get(source, 0) * 0.10
                adjusted_score = raw_score - (raw_score * penalty)
            else:
                adjusted_score = raw_score
                
            sig["adjusted_score"] = adjusted_score
            diversity_adjusted_signals.append(sig)
            seen_sources[source] = seen_sources.get(source, 0) + 1
            
        # Re-sort by adjusted score
        final_ranked = sorted(diversity_adjusted_signals, key=lambda x: x.get("adjusted_score", 0), reverse=True)
        top_signals = final_ranked[:3]
        
        represented_sources = {s.get("source") for s in top_signals}
        logger.info(f"Scout: Final top {len(top_signals)} signals. Represented sources: {represented_sources}")
        
        for signal in top_signals:
            insert_processed_signal(
                title=signal["title"],
                url=signal["source_url"],
                score=signal["adjusted_score"],
                topic_fingerprint=signal["title"],
                analysis_json=signal
            )
    except Exception as e:
        logger.error(f"Error scouting: {e}")
