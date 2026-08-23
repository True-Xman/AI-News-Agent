import json
from .gemini_client import send_gemini_request
from ..storage.operations import get_unprocessed_raw_signals, update_signal_filter

with open("prompts/sieve_prompt.md", "r") as f:
    SIEVE_PROMPT_TEMPLATE = f.read()

async def run_sieve():
    rows = get_unprocessed_raw_signals(20)
    for row in rows:
        url_hash, title, source, source_id, found_at, snippet = row[:6]
        prompt = SIEVE_PROMPT_TEMPLATE.replace("{{title}}", title).replace("{{source}}", source).replace("{{summary}}", snippet or "")
        
        try:
            response_text = await send_gemini_request(prompt)
            # Find JSON in response
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            data = json.loads(response_text[start:end])
            
            if data.get("decision") in ["KEEP", "DISCARD"]:
                update_signal_filter(
                    url_hash, 
                    data["decision"], 
                    data.get("reason", ""), 
                    data.get("confidence", 0.0),
                    data.get("scores")
                )
        except Exception as e:
            print(f"Error sieving {title}: {e}")
            # Errors are retryable (don't update DB)