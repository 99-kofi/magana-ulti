from flask import Flask, render_template, request, jsonify
import os
import base64
from magana_brain import get_gemini_response, clear_memory
from voice_engine import generate_hausa_audio
from document_handler import extract_text_from_file
import tempfile

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), "magana_uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/clear', methods=['POST'])
def clear_history():
    session_id = request.json.get('session_id')
    clear_memory(session_id)
    return jsonify({"status": "cleared"})

@app.route('/api/chat', methods=['POST'])
def chat():
    # Inputs
    text_input = request.form.get('text')
    voice_file = request.files.get('audio')
    doc_file = request.files.get('document')
    image_file = request.files.get('image')
    
    # Context
    mode = request.form.get('mode', 'chat')
    reasoning_mode = request.form.get('reasoning_mode', 'false')
    search_mode = request.form.get('search_mode', 'false')
    user_age = request.form.get('user_age', 'adult') 
    user_gender = request.form.get('user_gender', 'male')
    session_id = request.form.get('session_id', 'guest')
    
    response_data = {}
    
    if doc_file:
        filename = os.path.join(UPLOAD_FOLDER, doc_file.filename)
        doc_file.save(filename)
        extracted_text = extract_text_from_file(filename)
        # Docs usually use reasoning or teaching
        use_reasoning = "true" if reasoning_mode == "true" else "false"
        response_data = get_gemini_response(document_text=extracted_text, mode="teacher", user_age=user_age, user_gender=user_gender, session_id=session_id, reasoning_mode=use_reasoning)
        os.remove(filename)

    elif voice_file:
        temp = f"temp_{session_id}.wav"
        voice_file.save(temp)
        response_data = get_gemini_response(audio_file_path=temp, mode=mode, user_age=user_age, user_gender=user_gender, session_id=session_id, reasoning_mode=reasoning_mode, search_mode=search_mode)
        os.remove(temp)

    elif image_file:
        filename = os.path.join(UPLOAD_FOLDER, image_file.filename)
        image_file.save(filename)
        response_data = get_gemini_response(text_input=text_input, image_file_path=filename, mode="vision", user_age=user_age, user_gender=user_gender, session_id=session_id, reasoning_mode=reasoning_mode, search_mode=search_mode)
        os.remove(filename)

    else:
        response_data = get_gemini_response(text_input=text_input, mode=mode, user_age=user_age, user_gender=user_gender, session_id=session_id, reasoning_mode=reasoning_mode, search_mode=search_mode)

    return jsonify({
        "user_transcription": response_data.get('transcription', "📎 Input Received"),
        "bot_reply": response_data.get('reply_text', "Yi hakuri."),
        "english_translation": response_data.get('english_translation', ''),
        "proverb_used": response_data.get('proverb_used', ''),
        "steps": response_data.get('steps', []),
        "analysis": response_data.get('analysis', '')
    })

@app.route('/api/tts', methods=['POST'])
def tts():
    data = request.json
    text = data.get('text')
    voice_id = data.get('voice_id', 'Umar')
    
    audio_bytes = generate_hausa_audio(text, voice_id)
    if audio_bytes:
        audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
        return jsonify({"audio_base64": audio_b64})
    return jsonify({"error": "Failed"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
