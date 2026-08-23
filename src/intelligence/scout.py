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
        
        # Sort and take top 3 results for output
        sorted_signals = sorted(data.get("selected_signals", []), key=lambda x: x.get("score", 0), reverse=True)
        top_signals = sorted_signals[:3]
        
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
