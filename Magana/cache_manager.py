import os
import hashlib
import tempfile

# VERCEL FIX: Use the system's temporary directory
CACHE_DIR = os.path.join(tempfile.gettempdir(), "magana_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

def get_audio_cache_path(text, voice_id):
    unique_str = f"{voice_id}_{text}".encode('utf-8')
    file_hash = hashlib.md5(unique_str).hexdigest()
    filename = f"{file_hash}.mp3"
    return os.path.join(CACHE_DIR, filename)
