# llmmodel.py
import os

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Optionally set API key here or via environment variable
# openai.api_key = os.getenv("OPENAI_API_KEY")

def clean_caption(text: str) -> str:
    """
    Cleans text using OpenAI API if available.
    Falls back to returning raw text if API not available.
    """
    if not OPENAI_AVAILABLE or not getattr(openai, "api_key", None):
        return text  # skip if no API key

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content

    except Exception as e:
        # suppress missing API key errors only
        msg = str(e)
        if "api_key client option must be set" not in msg:
            print("LLM Error:", e)
        return text
