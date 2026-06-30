from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List
from test_ai import get_ai_response, SYSTEM_PROMPT
#EH
app = FastAPI(title="RoyalPMS AI API")

# Dictionary to hold chat memory for different users
sessions: Dict[str, List[dict]] = {}

# --- DATA MODELS ---
class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    session_id: str
    response: str

# --- ENDPOINTS ---
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    session_id = request.session_id
    user_message = request.message

    # Initialize memory for a new session
    if session_id not in sessions:
        sessions[session_id] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
    
    try:
        # Pass memory and message to our ai.py logic
        final_response = get_ai_response(
            session_memory=sessions[session_id], 
            user_message=user_message
        )
        
        return ChatResponse(
            session_id=session_id,
            response=final_response
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/chat/{session_id}")
async def clear_session(session_id: str):
    """Clears the chat history for a specific session."""
    if session_id in sessions:
        del sessions[session_id]
        return {"message": f"Session {session_id} cleared."}
    return {"message": "Session not found."}