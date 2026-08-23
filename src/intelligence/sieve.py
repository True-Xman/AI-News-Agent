import json
from .gemini_client import send_gemini_request
from ..storage.operations import get_unprocessed_raw_signals, update_signal_filter

with open("prompts/sieve_prompt.md", "r") as f:
    SIEVE_PROMPT_TEMPLATE = f.read()

async def run_sieve():
    rows = get_unprocessed_raw_signals(20)
    if not rows:
        return

    # Batch process signals (e.g., 5 at a time)
    batch_size = 5
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        
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
                print("Failed to find JSON array in response")
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
            print(f"Error sieving batch starting with {batch[0][1]}: {e}")
