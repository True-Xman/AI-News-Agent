import os
from google import genai

# Initialize client pointing to Gemini API
# Uses GOOGLE_API_KEY from environment
client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))

async def send_gemini_request(prompt: str) -> str:
    """Send prompt to Gemini via official google-genai SDK."""
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )
    return response.text
