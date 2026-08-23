import json
from .gemini_client import send_gemini_request
from ..storage.operations import get_keep_signals, insert_processed_signal

with open("prompts/scout_prompt.md", "r") as f:
    SCOUT_PROMPT_TEMPLATE = f.read()

async def run_scout():
    rows = get_keep_signals()
    if not rows:
        return
    
    # Batch candidates
    candidates = []
    for row in rows:
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
        
        for signal in data.get("selected_signals", []):
            insert_processed_signal(
                title=signal["title"],
                url=signal["source_url"],
                score=signal["score"],
                topic_fingerprint=signal["title"], # Simple fingerprint
                analysis_json=signal
            )
    except Exception as e:
        print(f"Error scouting: {e}")