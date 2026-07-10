from flask import Flask, render_template, request, session, redirect, url_for, flash
import requests
import os
import uuid

app = Flask(__name__)
app.secret_key = os.urandom(24) 

FASTAPI_URL = "http://127.0.0.1:8000"

# Server-side storage for UI chat histories. 
# Format: { "session_id": { "title": "Chat Title", "history": [] } }
ui_sessions = {}

@app.route('/', methods=['GET'])
def index():
    """Renders the main chat interface."""
    # Create a default session if the app just started and none exist
    if not ui_sessions:
        default_id = 'user_123'
        ui_sessions[default_id] = {"title": "New Chat", "history": []}
        session['session_id'] = default_id
    
    current_id = session.get('session_id', 'user_123')
    
    # Fallback if the session ID in the cookie doesn't exist on the server
    if current_id not in ui_sessions:
        current_id = list(ui_sessions.keys())[0]
        session['session_id'] = current_id

    # Format chats for the sidebar
    all_chats = [{"id": k, "title": v["title"]} for k, v in ui_sessions.items()]
        
    return render_template(
        'index.html', 
        chat_history=ui_sessions[current_id]["history"], 
        current_session_id=current_id,
        all_chats=all_chats
    )

@app.route('/send', methods=['POST'])
def send_message():
    """Sends the user's message to the FastAPI backend."""
    user_message = request.form.get('message')
    session_id = request.form.get('session_id')
    is_resend = request.form.get('is_resend')
    
    # FIX 1: If Flask restarted and wiped memory, recreate the session seamlessly
    if session_id not in ui_sessions:
        ui_sessions[session_id] = {"title": "Recovered Chat", "history": []}
        
    session['session_id'] = session_id

    if not user_message or not user_message.strip():
        flash("Message cannot be empty.", "error")
        return redirect(url_for('index'))

    chat_history = ui_sessions[session_id]["history"]

    # If this is a resend, pop the previous failed message to avoid duplicating
    if is_resend and chat_history and chat_history[-1].get('status') == 'error':
        chat_history.pop()

    # If this is the first message, rename the chat title
    if not chat_history:
        title = (user_message[:20] + "...") if len(user_message) > 20 else user_message
        ui_sessions[session_id]["title"] = title

    # Immediately save the user's message locally BEFORE the API call
    user_msg_obj = {'sender': 'user', 'text': user_message, 'status': 'sent'}
    chat_history.append(user_msg_obj)

    payload = {
        "session_id": session_id,
        "message": user_message
    }
    
    try:
        # FIX 2: Add a strict 10-second timeout. If the API is stuck, it fails fast 
        # instead of hanging your UI forever.
        response = requests.post(f"{FASTAPI_URL}/chat", json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            ai_response = data.get('response', '')
            chat_history.append({'sender': 'ai', 'text': ai_response})
        else:
            user_msg_obj['status'] = 'error'
            flash(f"AI API Error: {response.text}", "error")
            
    except requests.exceptions.RequestException:
         # Connection dropped or timed out
         user_msg_obj['status'] = 'error'
         flash("Failed to connect to the AI. Is the FastAPI server running?", "error")

    # Force Flask to save the cookie
    session.modified = True
    return redirect(url_for('index'))

@app.route('/new_chat', methods=['POST'])
def new_chat():
    """Generates a new session ID only if the current chat is not empty."""
    current_id = session.get('session_id')
    
    # 1. Prevent creation if the current chat exists but has no history
    if current_id and current_id in ui_sessions:
        if len(ui_sessions[current_id]["history"]) == 0:
            flash("Start typing !", "error")
            return redirect(url_for('index'))
            
    # 2. Otherwise, safely create the new chat
    new_id = f"user_{uuid.uuid4().hex[:8]}"
    ui_sessions[new_id] = {"title": "New Chat", "history": []}
    session['session_id'] = new_id
    session.modified = True
    
    return redirect(url_for('index'))

@app.route('/load_chat/<session_id>', methods=['GET'])
def load_chat(session_id):
    """Switches the active chat session and cleans up abandoned empty chats."""
    current_id = session.get('session_id')
    
    # 1. Check if we are leaving an empty chat (and not just reloading the same one)
    if current_id and current_id in ui_sessions and current_id != session_id:
        if len(ui_sessions[current_id]["history"]) == 0:
            
            # Remove it from the local Flask UI memory
            del ui_sessions[current_id]
            
            # Silently attempt to clear it from FastAPI memory just in case
            try:
                requests.delete(f"{FASTAPI_URL}/chat/{current_id}")
            except requests.exceptions.RequestException:
                pass # We can ignore connection errors for background cleanup

    # 2. Switch to the newly requested chat
    if session_id in ui_sessions:
        session['session_id'] = session_id
        session.modified = True
        
    return redirect(url_for('index'))

@app.route('/clear', methods=['POST'])
def clear_session():
    """Clears ONLY the current active session."""
    session_id = session.get('session_id')
    
    try:
        requests.delete(f"{FASTAPI_URL}/chat/{session_id}")
        flash(f"Memory cleared for session: {session_id}", "success")
    except requests.exceptions.RequestException as e:
        flash(f"Failed to clear FastAPI session memory: {e}", "error")
        
    if session_id in ui_sessions:
        ui_sessions[session_id]["history"] = []
        ui_sessions[session_id]["title"] = "New Chat"
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)