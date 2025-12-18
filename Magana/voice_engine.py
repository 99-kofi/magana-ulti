import os
import requests
from dotenv import load_dotenv
from cache_manager import get_audio_cache_path

load_dotenv()
YARNGPT_KEY = os.getenv("YARNGPT_API_KEY")

def generate_hausa_audio(text, voice_id="Umar"):
    # 1. Check Cache
    file_path = get_audio_cache_path(text, voice_id)
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            return f.read()

    # 2. Call API
    url = "https://yarngpt.ai/api/v1/tts"
    headers = {"Authorization": f"Bearer {YARNGPT_KEY}", "Content-Type": "application/json"}
    payload = {"text": text, "voice": voice_id, "response_format": "mp3"}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            with open(file_path, "wb") as f:
                f.write(response.content)
            return response.content
        return None
    except Exception as e:
        print(f"TTS Error: {e}")
        return None