import os
import requests
import json
import base64
from dotenv import load_dotenv
from web_search import search_web

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL = "gemini-3-flash-preview"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

CONVERSATION_HISTORY = {}

def clear_memory(session_id):
    if session_id in CONVERSATION_HISTORY:
        del CONVERSATION_HISTORY[session_id]
        return True
    return False

def get_cultural_prompt(user_age, user_gender, mode, reasoning_mode, search_mode):
    # 1. Honorifics
    honorifics = "Mallam / Malama"
    if user_age == "elder":
        honorifics = "Ranka ya daɗe / Baba" if user_gender == "male" else "Hajiya / Mama"
    elif user_age == "youth":
        honorifics = "Abokina / Ɗan'uwa"

    # 2. Persona & Tasks
    persona = "You are 'Magana', a wise Hausa AI."
    task_instructions = ""

    if search_mode == "true":
        persona += " You are in RESEARCH MODE (Mai Bincike)."
        task_instructions = """
        TASK:
        1. Use the WEB SEARCH RESULTS provided to answer the user.
        2. If asking for NEWS: Summarize key points in Hausa bullet points.
        3. If asking for EXPLANATION: Explain simply (like for a 10-year-old).
        4. Cite sources where possible.
        """
    elif reasoning_mode == "true":
        persona += " You are in DEEP THINKING MODE."
        task_instructions = """
        TASK:
        1. Break down the logic step-by-step (Mataki-mataki).
        2. Analyze pros/cons.
        3. Explain the 'Why' (Dalili).
        """
    elif mode == "teacher":
        persona = "You are 'Malam Magana', a teacher."
        task_instructions = "TASK: Educate clearly using proverbs."
    else:
        task_instructions = "TASK: Chat naturally with cultural respect."

    return f"""
    {persona}
    USER: {user_age} ({user_gender}). Honorifics: {honorifics}.
    
    RULES:
    1. Greeting is MANDATORY on first turn.
    2. Maintain Context (Memory).
    3. Use Hausa Proverbs (Karin Magana).
    
    {task_instructions}
    
    OUTPUT JSON:
    {{"transcription": "...", "reply_text": "...", "english_translation": "...", "proverb_used": "...", "steps": [], "analysis": "...", "intent": "..."}}
    """

def get_gemini_response(text_input=None, audio_file_path=None, document_text=None, mode="chat", user_age="adult", user_gender="male", session_id="default", reasoning_mode="false", search_mode="false"):
    headers = {"Content-Type": "application/json", "x-goog-api-key": API_KEY}

    if session_id not in CONVERSATION_HISTORY:
        CONVERSATION_HISTORY[session_id] = []

    current_parts = []
    history_text_rep = "" 

    # 1. Handle Search
    if search_mode == "true" and text_input:
        search_results = search_web(text_input)
        if search_results:
            current_parts.append({"text": f"{search_results}\n\nUSER QUESTION: {text_input}"})
            history_text_rep = f"[Searched: {text_input}]"
        else:
            current_parts.append({"text": text_input})
            history_text_rep = text_input
    
    # 2. Handle Docs / Audio / Text
    elif document_text:
        safe_text = document_text[:30000]
        current_parts.append({"text": f"SUMMARIZE THIS DOCUMENT IN HAUSA BULLET POINTS:\n{safe_text}"})
        history_text_rep = "[Document Uploaded]"
    elif audio_file_path:
        try:
            with open(audio_file_path, "rb") as f:
                audio_b64 = base64.b64encode(f.read()).decode("utf-8")
            current_parts.append({"inline_data": {"mime_type": "audio/wav", "data": audio_b64}})
            current_parts.append({"text": "Transcribe and respond."})
            history_text_rep = "[Audio Sent]"
        except:
            return {"reply_text": "Error reading audio.", "intent": "error"}
    elif not current_parts: # If not handled by search
        current_parts.append({"text": text_input})
        history_text_rep = text_input

    # 3. Add Reasoning Trigger
    if reasoning_mode == "true":
        current_parts.append({"text": "Yi tunani mai zurfi (Think deeply). Break it down step by step."})

    # 4. Construct Payload
    full_history = CONVERSATION_HISTORY[session_id].copy()
    request_contents = full_history + [{"role": "user", "parts": current_parts}]

    payload = {
        "contents": request_contents,
        "system_instruction": {"parts": [{"text": get_cultural_prompt(user_age, user_gender, mode, reasoning_mode, search_mode)}]},
        "generation_config": {"response_mime_type": "application/json"}
    }

    try:
        response = requests.post(URL, headers=headers, json=payload)
        raw_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(raw_text)

        if "transcription" in parsed and audio_file_path:
            history_text_rep = parsed["transcription"]

        CONVERSATION_HISTORY[session_id].append({"role": "user", "parts": [{"text": history_text_rep}]})
        CONVERSATION_HISTORY[session_id].append({"role": "model", "parts": [{"text": parsed.get("reply_text", "")}]})
        
        if len(CONVERSATION_HISTORY[session_id]) > 20:
             CONVERSATION_HISTORY[session_id] = CONVERSATION_HISTORY[session_id][-20:]

        return parsed

    except Exception as e:
        print(f"Brain Error: {e}")

        return {"reply_text": "Yi hakuri, network matsala.", "intent": "error"}
