import os
from dotenv import load_dotenv
from gradio_client import Client
from web_search import search_web

load_dotenv()

MODEL = os.getenv("LLM_GRADIO_SPACE", "yuntian-deng/ChatGPT")
client = Client(MODEL)

CONVERSATION_HISTORY = {}


def clear_memory(session_id):
    if session_id in CONVERSATION_HISTORY:
        del CONVERSATION_HISTORY[session_id]
        return True
    return False


def get_cultural_prompt(user_age, user_gender, mode, reasoning_mode, search_mode):
    honorifics = "Mallam / Malama"
    if user_age == "elder":
        honorifics = "Ranka ya daɗe / Baba" if user_gender == "male" else "Hajiya / Mama"
    elif user_age == "youth":
        honorifics = "Abokina / Ɗan'uwa"

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


def _extract_reply_text(result):
    if isinstance(result, str):
        return result

    if isinstance(result, (list, tuple)) and result:
        maybe_chat_history = result[-1]
        if isinstance(maybe_chat_history, list) and maybe_chat_history:
            last_turn = maybe_chat_history[-1]
            if isinstance(last_turn, (list, tuple)) and len(last_turn) >= 2:
                return str(last_turn[1])
        return str(result)

    return ""


def get_gemini_response(
    text_input=None,
    audio_file_path=None,
    document_text=None,
    image_file_path=None,
    mode="chat",
    user_age="adult",
    user_gender="male",
    session_id="default",
    reasoning_mode="false",
    search_mode="false",
):
    if session_id not in CONVERSATION_HISTORY:
        CONVERSATION_HISTORY[session_id] = []

    if audio_file_path:
        return {
            "reply_text": "This LLM endpoint currently supports text prompts only.",
            "intent": "error",
            "english_translation": "Please send text input for now.",
        }

    if mode == "vision" and image_file_path:
        return {
            "reply_text": "This LLM endpoint currently supports text prompts only.",
            "intent": "error",
            "english_translation": "Please use chat mode while vision support is disabled.",
        }

    history_text_rep = text_input or ""

    if search_mode == "true" and text_input:
        search_results = search_web(text_input)
        if search_results:
            text_input = f"{search_results}\n\nUSER QUESTION: {text_input}"
            history_text_rep = f"[Searched: {text_input}]"

    elif document_text:
        safe_text = document_text[:30000]
        text_input = f"SUMMARIZE THIS DOCUMENT IN HAUSA BULLET POINTS:\n{safe_text}"
        history_text_rep = "[Document Uploaded]"

    text_input = text_input or ""

    if reasoning_mode == "true":
        text_input = (
            f"{text_input}\n\nYi tunani mai zurfi (Think deeply). "
            "Break it down step by step."
        )

    system_prompt = get_cultural_prompt(
        user_age,
        user_gender,
        mode,
        reasoning_mode,
        search_mode,
    )
    llm_input = f"{system_prompt}\n\nUSER MESSAGE:\n{text_input}"

    try:
        chatbot_history = CONVERSATION_HISTORY[session_id].copy()
        result = client.predict(
            inputs=llm_input,
            top_p=1,
            temperature=1,
            chat_counter=len(chatbot_history),
            chatbot=chatbot_history,
            api_name="/predict",
        )

        reply_text = _extract_reply_text(result)
        CONVERSATION_HISTORY[session_id].append([history_text_rep, reply_text])

        if len(CONVERSATION_HISTORY[session_id]) > 20:
            CONVERSATION_HISTORY[session_id] = CONVERSATION_HISTORY[session_id][-20:]

        return {
            "transcription": history_text_rep,
            "reply_text": reply_text,
            "english_translation": "",
            "proverb_used": "",
            "steps": [],
            "analysis": "",
            "intent": "chat",
        }

    except Exception as e:
        print(f"Brain Error: {e}")

        friendly_error = "Yi hakuri, network na ɗan bada matsala. Da fatan za a sake gwadawa anjima."

        if "429" in str(e):
            friendly_error = "Yi hakuri, mun cikata aiki da yawa. Da fatan za a ɗan jira kaɗan."
        elif "401" in str(e) or "403" in str(e):
            friendly_error = "An kasa samun damar LLM endpoint. Duba saitunan sabar."

        return {
            "reply_text": friendly_error,
            "intent": "error",
            "proverb_used": "Hakuri maganin zaman duniya.",
            "english_translation": "Sorry, there is a network issue. Please try again later.",
        }
