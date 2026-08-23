import os
import google.generativeai as genai

def get_gemini_model():
    api_key = os.environ.get("GOOGLE_API_KEY")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-1.5-flash')

async def send_gemini_request(prompt):
    model = get_gemini_model()
    response = await model.generate_content_async(prompt)
    return response.text