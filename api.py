import json
import os
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
import redis

from graph import app as workflow_app

load_dotenv()

# Redis connection
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# State expiry in seconds (24 hours)
STATE_TTL = 86400

app = FastAPI(title="Social-to-Lead API", version="1.0.0")


# --- Redis State Helpers ---

def get_user_state(user_id: str) -> dict:
    """Get user state from Redis, or return fresh state if not found."""
    key = f"user_state:{user_id}"
    data = redis_client.get(key)
    
    if data:
        state = json.loads(data)
        # Rebuild message objects from stored dicts
        messages = []
        for msg in state.get("messages", []):
            if msg["type"] == "human":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["type"] == "ai":
                messages.append(AIMessage(content=msg["content"]))
        state["messages"] = messages
        return state
    
    # Fresh state for new user
    return {
        "messages": [],
        "user_info": {},
        "intents": "",
        "lead_captured": False
    }


def save_user_state(user_id: str, state: dict):
    """Save user state to Redis."""
    key = f"user_state:{user_id}"
    
    # Convert message objects to dicts for JSON serialization
    messages = []
    for msg in state.get("messages", []):
        if isinstance(msg, HumanMessage):
            messages.append({"type": "human", "content": msg.content})
        elif isinstance(msg, AIMessage):
            messages.append({"type": "ai", "content": msg.content})
    
    state_to_save = {
        "messages": messages,
        "user_info": state.get("user_info", {}),
        "intents": state.get("intents", ""),
        "lead_captured": state.get("lead_captured", False)
    }
    
    redis_client.setex(key, STATE_TTL, json.dumps(state_to_save))


def clear_user_state(user_id: str):
    """Clear user state from Redis."""
    key = f"user_state:{user_id}"
    redis_client.delete(key)


# --- API Endpoints ---

@app.get("/")
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "Social-to-Lead API"}


@app.post("/chat")
async def chat(request: Request):
    """
    Simple chat endpoint for testing.
    Expects JSON: {"user_id": "...", "message": "..."}
    """
    body = await request.json()
    user_id = body.get("user_id")
    message = body.get("message")
    
    if not user_id or not message:
        raise HTTPException(status_code=400, detail="user_id and message required")
    
    # Get current state, add message, run workflow
    state = get_user_state(user_id)
    state["messages"].append(HumanMessage(content=message))
    
    output_state = workflow_app.invoke(state)
    ai_response = output_state["messages"][-1].content
    
    # Save updated state
    save_user_state(user_id, output_state)
    
    return {
        "user_id": user_id,
        "response": ai_response,
        "lead_captured": output_state.get("lead_captured", False)
    }


@app.post("/chat/reset")
async def reset_chat(request: Request):
    """Reset conversation state for a user."""
    body = await request.json()
    user_id = body.get("user_id")
    
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    
    clear_user_state(user_id)
    return {"status": "ok", "message": f"State cleared for {user_id}"}


# --- WhatsApp Webhook (Twilio-compatible) ---

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...),
    To: str = Form(None),
    MessageSid: str = Form(None),
    AccountSid: str = Form(None),
):
    """
    Twilio WhatsApp webhook handler.
    Receives incoming messages and responds via TwiML.
    """
    # Extract phone number as user_id (remove 'whatsapp:' prefix)
    user_id = From.replace("whatsapp:", "").strip()
    message = Body.strip()
    
    # Handle reset command
    if message.lower() in ["reset", "restart", "start over"]:
        clear_user_state(user_id)
        response = MessagingResponse()
        response.message("Conversation reset! How can I help you today?")
        return Response(content=str(response), media_type="text/xml")
    
    # Get state, process message
    state = get_user_state(user_id)
    state["messages"].append(HumanMessage(content=message))
    
    try:
        output_state = workflow_app.invoke(state)
        ai_response = output_state["messages"][-1].content
        save_user_state(user_id, output_state)
    except Exception as e:
        ai_response = "Sorry, something went wrong. Please try again."
        print(f"Error processing message for {user_id}: {e}")
    
    # Build TwiML response
    response = MessagingResponse()
    response.message(ai_response)
    
    return Response(content=str(response), media_type="text/xml")


@app.get("/webhook/whatsapp")
async def whatsapp_webhook_verify(request: Request):
    """
    Verification endpoint for webhook setup.
    Just returns 200 OK for health checks.
    """
    return Response(content="OK", media_type="text/plain")


# --- Run with uvicorn ---

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
