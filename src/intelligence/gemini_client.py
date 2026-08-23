import os
import time
import asyncio
from google import genai
from google.genai.errors import APIError

# Initialize client pointing to Gemini API
# Uses GOOGLE_API_KEY from environment
client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))

async def send_gemini_request(prompt: str, max_retries: int = 3) -> str:
    """Send prompt to Gemini with exponential backoff for 429/503 errors."""
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt
            )
            return response.text
        except APIError as e:
            # 429: Resource Exhausted (Check status message for daily quota)
            if e.code == 429:
                if "daily" in str(e).lower() or "quota" in str(e).lower() or "exceeded" in str(e).lower():
                    print(f"Gemini Daily Quota Exhausted: {e}")
                    raise # Raise to stop retries entirely for quota
                
                # Temporary rate limit
                if attempt < max_retries - 1:
                    wait = (2 ** attempt)  # 1, 2, 4 seconds
                    print(f"Gemini Rate Limit (429), retrying in {wait}s...")
                    await asyncio.sleep(wait)
                    continue
            
            # 503: Service Unavailable
            elif e.code == 503 and attempt < max_retries - 1:
                wait = (2 ** attempt)
                print(f"Gemini Service Unavailable (503), retrying in {wait}s...")
                await asyncio.sleep(wait)
                continue
            
            raise
    return ""

