# LLM Chatbot with Key Failover and Response Caching

React + FastAPI + SQLite, with LiteLLM for the model calls, the response cache, and key failover.

## 1. Live URLs

- Frontend: `TODO: https://...`
- Backend: `TODO: https://...` (try `/health`)
- Demo video: `TODO`

## 2. Run locally

### With Docker

```bash
cp .env.example .env      # then put 2 real keys in LLM_API_KEYS
make up                   # frontend :3000, backend :8000
make down
```

`make up` copies `.env.example` to `.env` if you forgot. The SQLite file is at `/data/app.db` on the named volume `app_data`, so history survives `docker compose restart`.

### Without Docker

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export LLM_API_KEYS=key1,key2 ENABLE_FAILURE_SIMULATION=true DATABASE_URL=sqlite:///./app.db
uvicorn app.main:app --port 8000

# frontend (new terminal)
cd frontend
npm install
VITE_API_URL=http://localhost:8000 npm run dev    # http://localhost:3000
```

Run tests: `make test` (or `cd backend && python -m pytest -q`).

Offline mode: if a key starts with `mock` (for example `LLM_API_KEYS=mock-1,mock-2`), LiteLLM returns a fake reply with no network call. The whole flow, including cache and failover, still runs. The tests use this.

## 3. Design decisions

**Key fallback.** `LLM_API_KEYS` is split into `key_1`, `key_2`, ... in order. For each request the backend tries the keys in order with `litellm.acompletion(api_key=...)`. LiteLLM's own retries are off (`num_retries=0`) so one failed key moves on to the next immediately. Any error from a key (429, quota, 5xx, timeout, bad key, empty reply) counts as a failure. If every key fails, the API returns `503 {"detail": "all providers unavailable"}` and nothing is saved. `fallback_attempts` is the number of keys that failed before the one that answered.

**Caching.** LiteLLM's built-in in-memory cache (`Cache(type="local")`) is enabled. The cache key is built from the model and the full message list (system prompt + history + new message), so the same first message in a new session is a hit, and any different message is a miss. A hit is detected with LiteLLM's `cache_hit` flag, and returns `LLM_CACHE`, `key_id: null`, `fallback_attempts: 0`, and the token counts stored with the cached response. `temperature=0` keeps replies stable. The cache is in memory, so it is empty after a restart. A startup warm-up runs once so the first real cache hit is not slow.

**Failure simulation.** When `ENABLE_FAILURE_SIMULATION=true`, `X-Simulate-Failure` marks keys as failed for that request only. A simulated request skips the cache read, so a cached answer cannot hide the failover.

**SQLite session storage.** Two tables: `messages` (the required schema, plus an index on `session_id, id`) and `sessions` (stores the optional system prompt). The server reads the history, sends system prompt + history + new message to the model, then saves the user message and the reply in one transaction. If the call fails (503), nothing is saved. The schema is created at startup. A session exists only once it has a saved message, so an unknown id returns 404.

**Tokens and latency.** Tokens come from the provider's usage for that one request. They are never summed. `latency_ms` is measured on the server from request start to the model answer.

## 4. Verification

Replace `$B` with the backend URL.

```bash
B=http://localhost:8000
curl $B/health

# 1. Live call
curl -X POST $B/chat -H 'content-type: application/json' \
  -d '{"session_id":"s1","message":"What is the capital of France?"}'

# 2. Cache hit: same message, NEW session -> LLM_CACHE, key_id null, same reply
curl -X POST $B/chat -H 'content-type: application/json' \
  -d '{"session_id":"s2","message":"What is the capital of France?"}'

# 3. Failover: key_1 fails, key_2 answers
curl -X POST $B/chat -H 'content-type: application/json' -H 'X-Simulate-Failure: key_1=429' \
  -d '{"session_id":"s3","message":"Name a prime number"}'

# 4. All keys fail -> 503, nothing saved
curl -i -X POST $B/chat -H 'content-type: application/json' -H 'X-Simulate-Failure: *=429' \
  -d '{"session_id":"s4","message":"hello"}'
curl -i $B/sessions/s4/messages     # 404

# 5. Validation -> 422
curl -i -X POST $B/chat -H 'content-type: application/json' -d '{"session_id":"s5"}'

# 6. History from SQLite
curl $B/sessions/s1/messages
```

In the UI, open "Session settings" and type `key_1=429` in the simulate field to see failover. Every reply shows its source, model, latency, and input/output tokens for that request only.

## 5. Setup Used

- Editor: `TODO`
- AI tools: `TODO` (say honestly what you used them for)
- Model: Gemini through LiteLLM (`LLM_MODEL`)

## 6. Bonus features

- Optional per-session system prompt field in the UI.
- Failure-simulation field in the UI, so failover can be shown without curl.
- Offline `mock` key mode used by the tests.
- Startup warm-up of the cache path.

## Deployment notes

- Backend: deploy `backend/` as a Docker service. Set `LLM_API_KEYS`, `ALLOWED_ORIGINS` (your frontend URL), `ENABLE_FAILURE_SIMULATION=true`, and `DATABASE_URL=sqlite:////data/app.db` with a persistent volume mounted at `/data`. The app reads `PORT` if the host sets it.
- Frontend: deploy `frontend/` (Vercel, Netlify, etc.) with build command `npm run build`, output `dist`, and env `VITE_API_URL=<backend URL>`.
- Persistent storage: many free tiers wipe the disk on restart. If yours does, history will not survive there, so say so in the README and show persistence locally with `docker compose restart backend`.
