# Social-to-Lead Agentic Workflow

A conversational AI agent built with LangGraph that qualifies leads via WhatsApp. It handles greetings, answers product inquiries using RAG, and captures lead information.

## Setup

### Prerequisites

- Python 3.12.0
- Redis server
- Twilio account (for WhatsApp)
- ngrok (for local development)

### Step 1: Clone and Install Dependencies

```bash
cd Social-to-Lead-Agentic-Workflow
python -m venv myenv
myenv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

Create a `.env` file in the project root:

```
GOOGLE_API_KEY=your_google_api_key
GROQ_API_KEY=your_groq_api_key
REDIS_URL=redis://localhost:6379/0
```

### Step 3: Start Redis

Using Docker:
```bash
docker run -d --name redis -p 6379:6379 redis
```

### Step 4: Run the API Server

```bash
uvicorn api:app --reload --port 8000
```

### Step 5: Run Locally (CLI mode)

To test without WhatsApp:
```bash
python main.py
```

---

## Architecture Explanation

### Why LangGraph

I chose LangGraph because it models conversations as a state machine with nodes and edges, which fits perfectly for intent-based routing. Unlike vanilla LangChain which is more chain-oriented, LangGraph gives me conditional branching out of the box. Compared to AutoGen, it is lighter and does not require multi-agent conversations or complex setups. I just needed a simple graph where I classify intent, then route to the right handler. LangGraph made that easy without extra overhead.

### How State is Managed

The agent uses a `TypedDict` called `AgentState` with these fields:

- `messages`: Conversation history (list of HumanMessage/AIMessage)
- `intents`: Current classified intent
- `user_info`: Collected lead data (name, email, platform)
- `lead_captured`: Boolean flag for completion

For the API, state is persisted in Redis with a key pattern `user_state:{phone_number}`. Each user gets their own state that expires after 24 hours. When a message comes in, I load the state from Redis, run the graph, and save the updated state back.

---

## WhatsApp Integration via Webhooks

### How It Works

1. **Twilio as the Bridge**: Twilio provides a WhatsApp Business API sandbox. When a user sends a message to your Twilio WhatsApp number, Twilio forwards it to your webhook URL as an HTTP POST request.

2. **Webhook Endpoint**: The post `/webhook/whatsapp` endpoint in `api.py` receives the incoming message. Twilio sends form data with fields like `Body` (message text), `From` (sender's number), etc.

3. **Processing Flow**:
   - Extract the phone number from `From` field (remove `whatsapp:` prefix)
   - Load user state from Redis using phone number as key
   - Append the message to conversation history
   - Run the LangGraph workflow
   - Save updated state back to Redis
   - Return TwiML response with the AI reply

4. **TwiML Response**: Twilio expects a specific XML format called TwiML. I have used the `twilio` Python library to generate this:
   ```xml
   <Response><Message>Your reply here</Message></Response>
   ```

### Deployment Steps

1. Deploy your FastAPI app to a public server
2. Or use ngrok for local development: `ngrok http 8000`
3. Copy your public URL
4. Go to Twilio Console > Messaging > WhatsApp Sandbox > Sandbox Settings
5. Set "When a message comes in" to: `https://your-domain.com/webhook/whatsapp`
6. Set HTTP method to POST
7. Save and test by sending a WhatsApp message to your sandbox number

---

## Project Structure

```
.
├── api.py              # FastAPI server with Redis state and WhatsApp webhook
├── main.py             # CLI interface for local testing
├── graph.py            # LangGraph workflow definition
├── agents.py           # AgentState type and routing logic
├── tools.py            # Intent classifier, lead capture, generic responder
├── rag_engine.py       # RAG-based product inquiry handler
├── config.py           # LLM and embeddings configuration
├── knowledge_base.json # Product/pricing data
├── load_base.py        # Knowledge base loader
└── requirements.txt    # Python dependencies
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/chat` | JSON chat endpoint for testing |
| POST | `/chat/reset` | Reset user conversation state |
| POST | `/webhook/whatsapp` | Twilio WhatsApp webhook |
| GET | `/webhook/whatsapp` | Webhook verification |

### Example: Test via curl

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test123", "message": "What plans do you offer?"}'
```
<img width="1440" height="900" alt="image" src="https://github.com/user-attachments/assets/6d8e0b34-2775-41f8-80df-4ca93f813af5" />

