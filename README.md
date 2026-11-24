# Lyftr AI – LLM Chatbot with Key Failover and Response Caching

A full-stack AI chatbot built using **React, FastAPI, SQLite, and LiteLLM**. The application supports multiple API keys with automatic failover, response caching, multi-turn conversations, session-based message history, and request-level token and latency tracking.

## 1. Live URLs

- **Frontend:** https://lyftr-chat-91kph1uld-aahana.vercel.app/
- **Backend:** `https://lyftr-chat-app-u4fb.onrender.com
- **Backend Health Check:** `https://lyftr-chat-app-u4fb.onrender.com/health

> Live deployment links will be added after deployment.

## 2. Tech Stack

| Component | Technology |
|---|---|
| Frontend | React, Vite, CSS |
| Backend | Python, FastAPI |
| LLM Integration | LiteLLM |
| AI Model | Gemini |
| Database | SQLite |
| Caching | LiteLLM Local Cache |
| Containerization | Docker, Docker Compose |
| Testing | Pytest |
| Version Control | Git, GitHub |

## 3. Features

- **Multiple API Key Support:** Supports multiple LLM API keys.
- **Automatic Key Failover:** Automatically switches to another available key when a provider request fails.
- **Response Caching:** Uses LiteLLM's local cache to avoid repeated model calls for identical requests.
- **Multi-turn Conversations:** Maintains conversation context using session-based message history.
- **SQLite Persistence:** Stores user messages and assistant responses in SQLite.
- **Token Tracking:** Reports input and output tokens for individual requests.
- **Latency Tracking:** Measures model response latency.
- **Failure Simulation:** Allows provider failures to be simulated for testing failover behavior.
- **System Prompt Support:** Supports an optional custom system prompt for each session.
- **Offline Mock Mode:** Supports mock API keys for testing without making real LLM network calls.

## 4. Run Locally

### Prerequisites

- Python 3.10+
- Node.js and npm
- Docker Desktop and Docker Compose (for Docker setup)
- Two valid LLM API keys for live inference

### A. Run with Docker

Clone the repository:

```bash
git clone https://github.com/Aahanaaa13/lyftr-chat-app.git
cd lyftr-chat-app
```

Create your environment file:

```bash
cp .env.example .env
```

Add your actual API keys to `.env`:

```env
LLM_API_KEYS=your_api_key_1,your_api_key_2
LLM_MODEL=gemini/gemini-3.5-flash-lite
DATABASE_URL=sqlite:////data/app.db
ALLOWED_ORIGINS=http://localhost:3000
ENABLE_FAILURE_SIMULATION=true
LLM_TIMEOUT_SECONDS=30
LLM_MAX_TOKENS=1024
VITE_API_URL=http://localhost:8000
```

Never commit your actual `.env` file or expose your API keys publicly.

Build and start the application:

```bash
make up
```

Application URLs:

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Health Check: http://localhost:8000/health

Stop the application:

```bash
make down
```

The SQLite database is stored at `/data/app.db` inside the backend container and uses the Docker named volume `app_data`. This allows database history to survive container restarts.

### B. Run Without Docker

**Backend setup**

```bash
cd backend

python -m venv .venv
```

Activate the environment:

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements-dev.txt
```

Configure environment variables.

Windows PowerShell:

```powershell
$env:LLM_API_KEYS="your_api_key_1,your_api_key_2"
$env:LLM_MODEL="gemini/gemini-3.5-flash-lite"
$env:DATABASE_URL="sqlite:///./app.db"
$env:ENABLE_FAILURE_SIMULATION="true"
```

Linux/macOS:

```bash
export LLM_API_KEYS="your_api_key_1,your_api_key_2"
export LLM_MODEL="gemini/gemini-3.5-flash-lite"
export DATABASE_URL="sqlite:///./app.db"
export ENABLE_FAILURE_SIMULATION=true
```

Start the backend:

```bash
uvicorn app.main:app --reload --port 8000
```

**Frontend setup**

Open another terminal:

```bash
cd frontend
npm install
```

Start the frontend:

```bash
npm run dev -- --host 0.0.0.0 --port 3000
```

Open:

http://localhost:3000

For local development, configure `VITE_API_URL` to point to the backend URL if it is not already configured.

## 5. API Endpoints

### GET /health

Checks backend health and configuration readiness.

Example response:

```json
{
  "status": "ok",
  "keys_configured": 2,
  "cache_enabled": true
}
```

### POST /chat

Sends a message to the chatbot.

Request:

```json
{
  "session_id": "session-001",
  "message": "What is the capital of France?",
  "system_prompt": "You are a helpful assistant."
}
```

Example response:

```json
{
  "session_id": "session-001",
  "reply": "The capital of France is Paris.",
  "metadata": {
    "resolution_source": "LIVE_INFERENCE",
    "model": "gemini/gemini-3.5-flash-lite",
    "latency_ms": 1200,
    "input_tokens": 21,
    "output_tokens": 7,
    "key_id": "key_1",
    "fallback_attempts": 0
  }
}
```

The `resolution_source` field identifies whether the response came from live inference or the cache:

- `LIVE_INFERENCE`
- `LLM_CACHE`

For cached responses, `key_id` is null and `fallback_attempts` is zero.

### GET /sessions/{session_id}/messages

Retrieves the conversation history for a session in chronological order.

Example:

```bash
curl http://localhost:8000/sessions/session-001/messages
```

Returns HTTP 404 if the requested session does not exist.

### Error Handling

| HTTP Status | Description |
|---|---|
| 422 | Invalid request or input validation failure |
| 404 | Session not found |
| 503 | All configured providers unavailable |

Failed requests are not stored in conversation history.

## 6. Design Decisions

### A. Multiple API Keys and Automatic Failover

The application supports multiple API keys through the `LLM_API_KEYS` environment variable.

Example:

```env
LLM_API_KEYS=key1,key2
```

Keys are assigned identifiers such as `key_1`, `key_2`, etc.

For each live request:

1. The backend attempts inference using the first configured key.
2. If the request fails, the next key is attempted.
3. The process continues until a provider returns a valid response or all keys fail.
4. If every key fails, the API returns HTTP 503.

LiteLLM retries are disabled at the individual call level using `num_retries=0`, allowing the application to control the failover sequence.

The `fallback_attempts` field records the number of failed keys before a successful response.

### B. Response Caching

The application uses LiteLLM's built-in local cache.

The cache key is based on:

- Selected model
- Complete message list
- System prompt
- Conversation history
- Current user message

This ensures that different conversation contexts are treated as different requests.

When an identical request is found in the cache:

- The cached response is returned.
- `resolution_source` is set to `LLM_CACHE`.
- `key_id` is null.
- `fallback_attempts` is zero.
- Cached token usage is returned.

The cache is in-memory, so it is cleared when the backend process restarts.

### C. Failure Simulation

The application supports an optional `X-Simulate-Failure` HTTP header.

Failure simulation is enabled through:

```env
ENABLE_FAILURE_SIMULATION=true
```

Examples:

```text
key_1=429
```

Simulates a rate-limit failure for the first key.

```text
key_1=429,key_2=500
```

Simulates failures for both keys.

```text
*=429
```

Simulates failures for all configured keys.

Supported simulated HTTP status codes:

- 429
- 500
- 502
- 503

Simulation is request-specific and does not permanently modify API key availability.

Simulated requests skip the cache read so that a cached response cannot hide failover behavior.

### D. SQLite Session Storage

SQLite is used to persist conversation history.

The database contains:

- `messages`: Stores user and assistant messages.
- `sessions`: Stores session-specific system prompt information.

For a successful chat request:

1. The backend retrieves the session history.
2. The system prompt and conversation history are assembled.
3. The new user message is sent to the LLM.
4. The user message and assistant response are saved in a transaction.

Failed inference requests are not stored.

Unknown session IDs return HTTP 404.

### E. Token Usage and Latency

Each response includes:

- Input tokens
- Output tokens
- Model name
- Response latency
- Resolution source
- API key identifier
- Number of fallback attempts

Token counts represent the individual request rather than cumulative session usage.

## 7. Verification and Testing

The backend includes automated tests covering API behavior, caching, failover, session history, validation, and error handling.

Run the tests:

```bash
cd backend
python -m pytest -v
```

Or from the project root:

```bash
make test
```

### Manual API Verification

Set the backend URL:

```bash
B=http://localhost:8000
```

**1. Health Check**

```bash
curl $B/health
```

**2. Live Inference**

```bash
curl -X POST $B/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"s1","message":"What is the capital of France?"}'
```

**3. Cache Verification**

Send the same message using a new session ID:

```bash
curl -X POST $B/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"s2","message":"What is the capital of France?"}'
```

Expected behavior: `LLM_CACHE` if the matching request is already cached.

**4. Failover Verification**

```bash
curl -X POST $B/chat \
  -H "Content-Type: application/json" \
  -H "X-Simulate-Failure: key_1=429" \
  -d '{"session_id":"s3","message":"Name a prime number"}'
```

Expected behavior: the backend skips the simulated failure for `key_1` and attempts `key_2`.

**5. All Providers Unavailable**

```bash
curl -i -X POST $B/chat \
  -H "Content-Type: application/json" \
  -H "X-Simulate-Failure: *=429" \
  -d '{"session_id":"s4","message":"Hello"}'
```

Expected response:

```json
{
  "detail": "all providers unavailable"
}
```

**6. Verify Failed Requests Are Not Stored**

```bash
curl -i $B/sessions/s4/messages
```

Expected response: HTTP 404.

**7. Input Validation**

```bash
curl -i -X POST $B/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"s5"}'
```

Expected response: HTTP 422.

**8. Retrieve Conversation History**

```bash
curl $B/sessions/s1/messages
```

Expected behavior: returns messages in chronological order.

### Automated Test Coverage

The test suite covers:

- Health endpoint
- Live inference followed by cache hit
- Different messages producing cache misses
- Per-request token accounting
- Session isolation and history retrieval
- Unknown session handling
- Request validation
- API key failover
- Failover with cached messages
- All-provider failure handling
- Failure simulation configuration
- System prompt persistence

## 8. Setup Used

- **Editor:** Visual Studio Code
- **Programming Languages:** Python and JavaScript
- **AI Tools:** ChatGPT for implementation guidance, debugging assistance, and documentation refinement.
- **LLM Integration:** Gemini through LiteLLM.
- **Version Control:** Git and GitHub.
- **Containerization:** Docker and Docker Compose.
- **Testing:** Pytest.

## 9. Bonus Features

- Optional per-session system prompt configuration.
- Frontend failure-simulation controls for demonstrating key failover.
- Offline mock-key mode for testing without external LLM API calls.
- Startup cache warm-up.
- Request-level metadata displayed alongside assistant responses.
- Persistent SQLite storage using Docker named volumes.

## 10. Project Structure

```text
lyftr-chat-app/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── llm.py
│   │   ├── main.py
│   │   └── schemas.py
│   │
│   ├── scripts/
│   │   └── check_keys.py
│   │
│   ├── tests/
│   │   ├── conftest.py
│   │   └── test_api.py
│   │
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js
│   │   ├── main.jsx
│   │   └── styles.css
│   │
│   ├── Dockerfile
│   ├── index.html
│   ├── nginx.conf
│   └── package.json
│
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Makefile
└── README.md
```

## 11. Deployment Notes

### Backend Deployment

The backend can be deployed as a Docker service using the `backend/` directory.

Configure the following environment variables:

- `LLM_API_KEYS`
- `LLM_MODEL`
- `DATABASE_URL`
- `ALLOWED_ORIGINS`
- `ENABLE_FAILURE_SIMULATION`
- `LLM_TIMEOUT_SECONDS`
- `LLM_MAX_TOKENS`

For persistent SQLite storage, mount a persistent volume at `/data` and configure:

```env
DATABASE_URL=sqlite:////data/app.db
```

The backend application reads the `PORT` environment variable when provided by the hosting platform.

### Frontend Deployment

The frontend can be deployed using Vercel or another static hosting provider.

Configure:

- Root Directory: `frontend`
- Build Command: `npm run build`
- Output Directory: `dist`
- Environment Variable: `VITE_API_URL`

Set `VITE_API_URL` to the deployed backend URL.

### Storage Considerations

SQLite persistence depends on the hosting provider's storage configuration.

Some free hosting plans use ephemeral storage, which may be cleared after a restart or redeployment. A persistent disk or volume is required to preserve conversation history across such events.

---

**Author:** Aahana Mittal

**Repository:** https://github.com/Aahanaaa13/lyftr-chat-app
