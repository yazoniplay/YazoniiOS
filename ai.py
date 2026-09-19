import os
import aiohttp

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

SYSTEM_PROMPT = """You are YAZONI's Right Hand Man.
Be direct, sharp, useful, and concise.
Help with coding, Minecraft, projects, business ideas, school, planning, and general questions.
Use a slightly witty Discord-friendly tone, but stay accurate.
Never claim you performed an action unless the bot actually performed it.
If unsure, say so instead of inventing facts."""

async def ask_gemini(prompt):
    if not GEMINI_API_KEY:
        return "Gemini is not configured. Add GEMINI_API_KEY to the bot environment."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
    }
    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers, timeout=45) as response:
            data = await response.json(content_type=None)
            if response.status != 200:
                return "Gemini API error: " + data.get("error", {}).get("message", "Unknown error")
            return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "Gemini returned no text.")
