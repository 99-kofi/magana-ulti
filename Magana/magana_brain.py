import os
import json
import base64
from dotenv import load_dotenv
from google import genai
from google.genai import types
from web_search import search_web

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL = "gemini-3-flash-preview"
client = genai.Client(api_key=API_KEY)

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
    elif mode == "vision":
        persona += " You are in VISION MODE (Mai Gani)."
        task_instructions = """
        TASK:
        1. Describe the image provided in Hausa with cultural context.
        2. Identify objects, colors, and the general mood.
        3. If there is text in the image, transcribe and translate it to Hausa.
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

def get_gemini_response(text_input=None, audio_file_path=None, document_text=None, image_file_path=None, mode="chat", user_age="adult", user_gender="male", session_id="default", reasoning_mode="false", search_mode="false"):
    
    if session_id not in CONVERSATION_HISTORY:
        CONVERSATION_HISTORY[session_id] = []

    current_parts = []
    history_text_rep = "" 

    # 1. Handle Search
    if search_mode == "true" and text_input:
        search_results = search_web(text_input)
        if search_results:
            current_parts.append(types.Part.from_text(text=f"{search_results}\n\nUSER QUESTION: {text_input}"))
            history_text_rep = f"[Searched: {text_input}]"
        else:
            current_parts.append(types.Part.from_text(text=text_input))
            history_text_rep = text_input
    
    # 2. Handle Docs / Audio / Text
    elif document_text:
        safe_text = document_text[:30000]
        current_parts.append(types.Part.from_text(text=f"SUMMARIZE THIS DOCUMENT IN HAUSA BULLET POINTS:\n{safe_text}"))
        history_text_rep = "[Document Uploaded]"
    elif audio_file_path:
        try:
            with open(audio_file_path, "rb") as f:
                audio_bytes = f.read()
            # SDK handles base64 implicitly via from_bytes or providing bytes directly? 
            # Looking at docs, from_bytes takes raw bytes and mime_type.
            current_parts.append(types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"))
            current_parts.append(types.Part.from_text(text="Transcribe and respond."))
            history_text_rep = "[Audio Sent]"
        except Exception as e:
            print(f"Audio Error: {e}")
            return {"reply_text": "Error reading audio.", "intent": "error"}
    elif mode == "vision" and image_file_path:
        try:
            mime_type = "image/jpeg"
            if image_file_path.endswith(".png"): mime_type = "image/png"
            elif image_file_path.endswith(".webp"): mime_type = "image/webp"

            with open(image_file_path, "rb") as f:
                img_bytes = f.read()
            
            current_parts.append(types.Part.from_bytes(data=img_bytes, mime_type=mime_type))
            
            prompt_text = text_input if text_input else "Describe this image in detail in Hausa."
            current_parts.append(types.Part.from_text(text=prompt_text))
            history_text_rep = f"[Image Uploaded: {prompt_text}]"
        except Exception as e:
            print(f"Vision Error: {e}")
            return {"reply_text": "An samu matsala wajen duba hoton.", "intent": "error"}
    elif not current_parts: # If not handled by search or vision
        current_parts.append(types.Part.from_text(text=text_input))
        history_text_rep = text_input

    # 3. Add Reasoning Trigger
    if reasoning_mode == "true":
        current_parts.append(types.Part.from_text(text="Yi tunani mai zurfi (Think deeply). Break it down step by step."))

    # 4. Construct Payload
    # The history must be converted to proper Content objects if we want to be strict, 
    # but the SDK usually accepts dicts mixed with Content objects.
    # However, to be safe, let's keep the history structure as is (dicts) and 
    # append the new user message. The SDK `contents` parameter accepts a list of contents.
    
    full_history = CONVERSATION_HISTORY[session_id].copy()
    
    # We need to construct the new user content item
    new_content = {"role": "user", "parts": current_parts}
    full_history.append(new_content)

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=full_history,
            config=types.GenerateContentConfig(
                system_instruction=get_cultural_prompt(user_age, user_gender, mode, reasoning_mode, search_mode),
                response_mime_type="application/json"
            )
        )
        
        parsed = json.loads(response.text)

        if "transcription" in parsed and audio_file_path:
            history_text_rep = parsed["transcription"]

        # Update History
        # We need to serialize the parts back to simple dicts for history if we used Part objects
        # actually CONVERSATION_HISTORY stores simple dicts. 
        # But `current_parts` contains `types.Part` objects now.
        # We should probably convert them or leave them if the SDK can handle re-sending them.
        # To be safe for serialization (if we ever did that), we might want text, but for now memory is fine.
        # BUT: reusing Part objects in future calls is fine.
        
        CONVERSATION_HISTORY[session_id].append({"role": "user", "parts": current_parts})
        CONVERSATION_HISTORY[session_id].append({"role": "model", "parts": [{"text": parsed.get("reply_text", "")}]})
        
        if len(CONVERSATION_HISTORY[session_id]) > 20:
             CONVERSATION_HISTORY[session_id] = CONVERSATION_HISTORY[session_id][-20:]

        return parsed

    except Exception as e:
        # Log the full error for the developer
        print(f"Brain Error: {e}")
        
        # User-friendly generic error message in Hausa
        friendly_error = "Yi hakuri, network na ɗan bada matsala. Da fatan za a sake gwadawa anjima."
        
        # Determine if it's a quota issue (heuristic)
        if "429" in str(e):
            friendly_error = "Yi hakuri, mun cikata aiki da yawa. Da fatan za a ɗan jira kaɗan."

        return {
            "reply_text": friendly_error,
            "intent": "error",
            "proverb_used": "Hakuri maganin zaman duniya.", # Patience is the cure for worldly living
            "english_translation": "Sorry, there is a network issue. Please try again later."
        }
