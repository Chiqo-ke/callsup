# CALLSUP Backend — Architecture & API Documentation

> **Version:** 0.1.0  
> **Framework:** FastAPI (Python)  
> **Base URL (local):** `http://127.0.0.1:8000`

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Technology Stack](#2-technology-stack)
3. [Project Structure](#3-project-structure)
4. [Data Models](#4-data-models)
5. [Authentication Flow](#5-authentication-flow)
6. [Data Flow Diagrams](#6-data-flow-diagrams)
7. [API Endpoints](#7-api-endpoints)
   - [Health](#71-health)
   - [Authentication](#72-authentication)
   - [Audio Ingest & Transcripts](#73-audio-ingest--transcripts)
   - [Voice / LLM Conversation](#74-voice--llm-conversation)
   - [Escalation Queue](#75-escalation-queue)
   - [Escalation Rules](#76-escalation-rules)
   - [Business Context](#77-business-context)
   - [Metrics](#78-metrics)
8. [Escalation Lifecycle](#8-escalation-lifecycle)
9. [Storage Layer](#9-storage-layer)
10. [External Services](#10-external-services)
11. [PII Redaction](#11-pii-redaction)
12. [Environment Variables Reference](#12-environment-variables-reference)
13. [Security Controls](#13-security-controls)

---

## 1. Architecture Overview

CALLSUP is a **multi-tenant AI call-centre backend**. Each registered business (tenant) gets an isolated workspace identified by a `business_id` UUID. The system handles:

- **Audio ingestion** — accept raw call audio, transcribe it, encrypt and store it
- **Voice AI chat** — real-time LLM-powered call agent via OpenCode server
- **Escalation detection** — two-layer detection (LLM tool-calling + XML fallback) that creates tickets and pushes them live to human agent dashboards via Server-Sent Events (SSE)
- **Business configuration** — per-tenant context documents and escalation rules that shape the LLM's behaviour

```
┌───────────────────────────────────────────────────────────────────┐
│                        Frontend / Client                          │
│     (React SPA on localhost:5173 or localhost:8081)               │
└────────────────┬──────────────────────┬───────────────────────────┘
                 │ HTTP/REST            │ SSE (escalation stream)
                 ▼                      ▼
┌────────────────────────────────────────────────────────────────────┐
│                  CALLSUP Audio Engine API                          │
│                  FastAPI  ·  Port 8000                             │
│                                                                    │
│  ┌──────────┐  ┌───────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │  /auth   │  │  /audio   │  │  /escalation │  │  /context   │  │
│  │  Router  │  │  Routes   │  │  -queue      │  │  Router     │  │
│  └──────────┘  └─────┬─────┘  │  -rules      │  └─────────────┘  │
│                       │        └──────────────┘                    │
│               ┌───────┴──────┐                                     │
│               │AudioRepository│  ← Fernet-encrypted audio files    │
│               │  (storage.py)│     + in-memory transcript cache    │
│               └──────────────┘                                     │
└──────┬──────────────┬──────────────────────────────────────────────┘
       │              │
       │              ▼
       │   ┌───────────────────┐
       │   │  OpenCode Server  │  LLM session management
       │   │  localhost:4096   │  (POST /session, POST /session/{id}/message)
       │   └───────────────────┘
       │
       ├──────────────────────────────────────┐
       │                                      │
       ▼                                      ▼
┌──────────────────┐                ┌──────────────────────┐
│  LLM Adapter     │                │  OpenAI API          │
│  localhost:9100  │                │  - Whisper STT       │
│  POST /v1/generate│               │  - TTS (tts-1)       │
└──────────────────┘                └──────────────────────┘
       (tool-calling escalation      (+ RapidAPI Whisper as
        decision + rule refinement)   primary STT provider)

┌──────────────────────────────────────────────────────┐
│               Flat-file JSON / Markdown Storage      │
│  data/                                               │
│  ├── users.json                                      │
│  ├── audio/{conv_id}.bin              (encrypted)    │
│  ├── escalations/{biz_id}/                           │
│  │   ├── queue.json                                  │
│  │   └── rules.json                                  │
│  └── contexts/{biz_id}/                              │
│      ├── index.json                                  │
│      └── {item_id}.md                                │
└──────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack

| Component | Technology |
|-----------|-----------|
| Web framework | FastAPI (Python 3.11+) |
| Validation | Pydantic v2 (BaseModel, field_validator) |
| Authentication | JWT / PyJWT, HS256, Bearer tokens |
| TLS enforcement | Custom middleware (HSTS, X-Frame-Options, X-Content-Type-Options) |
| Audio encryption | Fernet (cryptography library) |
| STT (primary) | RapidAPI Whisper (`speech-to-text-ai.p.rapidapi.com`) |
| STT (fallback) | OpenAI Whisper-1 |
| TTS | OpenAI TTS-1 (voice: alloy, onyx, nova, …) |
| LLM conversation | OpenCode server (session-based, localhost:4096) |
| Escalation LLM | LLM Adapter service (localhost:9100, `/v1/generate`) |
| Real-time push | Server-Sent Events (SSE) via asyncio.Queue bus |
| Metrics | Prometheus (`prometheus_client`, exposed at `/metrics`) |
| Settings | pydantic-settings from `.env` (prefix `CALLSUP_AUDIO_ENGINE_`) |
| Storage | Flat JSON files + Markdown files (no database) |

---

## 3. Project Structure

```
callsup/
├── app/
│   ├── main.py             # App factory (create_app), all audio/voice routes
│   ├── auth.py             # /auth router — register, login, /me
│   ├── config.py           # Settings (pydantic-settings)
│   ├── models.py           # Shared Pydantic data models
│   ├── storage.py          # AudioRepository — encrypted audio & transcript store
│   ├── transcription.py    # STT wrappers (RapidAPI Whisper, OpenAI Whisper)
│   ├── business_context.py # Helpers to load business name & context for LLM
│   ├── context_store.py    # /context router — CRUD for context documents
│   ├── escalation_queue.py # /escalation-queue router — tickets + SSE stream
│   ├── escalation_rules.py # /escalation-rules router — CRUD for rules
│   ├── pii_redaction.py    # Regex PII scrubbing (email, phone, SSN, card)
│   ├── metrics.py          # Prometheus counters/histograms
│   └── logging_config.py   # Structured logging setup
├── svc_llm_adapter.py      # Mock LLM adapter (for local smoke-testing)
├── data/                   # Runtime data (git-ignored)
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_pii_redaction.py
│   └── test_transcription.py
├── .env                    # Environment variables (not committed)
├── requirements.txt
└── openapi.yaml
```

---

## 4. Data Models

### 4.1 TranscriptSegment

Represents a single timed segment from a call transcript.

```python
class TranscriptSegment(BaseModel):
    business_id: str
    conv_id: str
    segment_id: str
    speaker: Literal["customer", "agent"] | None
    start_ts: datetime
    end_ts: datetime
    text: str
    confidence: float
```

### 4.2 EscalationRule

A business-defined rule that triggers escalation to a human agent.

```python
class EscalationRule(BaseModel):
    id: str                          # UUID
    business_id: str
    rule_text: str                   # Human-authored rule
    ai_refined_text: str | None      # LLM-rewritten version (injected into prompt)
    priority: Literal["high", "medium", "low"]
    is_active: bool
    created_at: str                  # ISO-8601 UTC
    updated_at: str
```

### 4.3 EscalationTicket

Created when the LLM decides a call needs a human agent.

```python
class EscalationTicket(BaseModel):
    id: str                          # UUID
    business_id: str
    conv_id: str | None
    session_id: str
    reason: str                      # Why escalation was triggered
    priority: Literal["high", "medium", "low"]
    summary: str | None
    rule_triggered: str | None       # Which rule ID caused escalation
    status: Literal["pending", "claimed", "resolved"]
    created_at: str                  # ISO-8601 UTC
    claimed_by: str | None           # Agent username who claimed it
    resolved_at: str | None
    conversation_history: list[dict] # Full chat messages up to escalation
```

### 4.4 UserRecord (internal)

Stored in `data/users.json`.

```python
class UserRecord(BaseModel):
    id: str          # UUID
    username: str
    email: str
    password_hash: str  # SHA-256 hex
    salt: str           # 16-byte hex (secrets.token_hex)
    business_id: str    # UUID — tenant identifier
    business_name: str
    created_at: str
```

### 4.5 ContextItem

Business knowledge document used to build the LLM system prompt.

```python
class ContextItem(BaseModel):
    id: str
    label: str
    type: str          # "manual" | "file"
    file_name: str | None
    is_alert: bool     # True → appears under "ACTIVE ALERTS" in prompt
    expires_at: str | None  # ISO-8601; None = never expires
    created_at: str
    updated_at: str
    content: str       # Markdown body
```

---

## 5. Authentication Flow

All routes except `/health`, `/auth/register`, `/auth/login`, and `/escalation-queue/stream` require a JWT Bearer token.

```
Client                          Backend
  │                                │
  │  POST /auth/register           │
  │  {username, email, password,   │
  │   business_name}               │
  │ ─────────────────────────────► │
  │                                │  1. Validate username (≥3 chars, alphanumeric+-_)
  │                                │  2. Validate password (≥8 chars)
  │                                │  3. Generate salt (secrets.token_hex(16))
  │                                │  4. Hash password: SHA-256(password + salt)
  │                                │  5. Create UserRecord with new UUID business_id
  │                                │  6. Append to data/users.json
  │                                │  7. Sign JWT (HS256, 24hr expiry)
  │  {access_token, token_type,    │
  │   business_id, username,       │
  │   business_name}               │
  │ ◄───────────────────────────── │
  │                                │
  │  POST /auth/login              │
  │  {username, password}          │
  │ ─────────────────────────────► │
  │                                │  1. Find user by username
  │                                │  2. Verify: secrets.compare_digest(
  │                                │       SHA-256(password+salt), stored_hash)
  │                                │  3. Sign & return JWT
  │  {access_token, ...}           │
  │ ◄───────────────────────────── │
  │                                │
  │  GET /auth/me                  │
  │  Authorization: Bearer <token> │
  │ ─────────────────────────────► │
  │                                │  1. Decode JWT, extract sub (user_id)
  │                                │  2. Load UserRecord from users.json
  │  {id, username, email,         │
  │   business_id, business_name,  │
  │   created_at}                  │
  │ ◄───────────────────────────── │
```

**JWT payload structure:**
```json
{
  "sub": "user-uuid",
  "username": "alice",
  "business_id": "biz-uuid",
  "iat": 1700000000,
  "exp": 1700086400
}
```

---

## 6. Data Flow Diagrams

### 6.1 Audio Ingest Flow

```
Client uploads audio file
        │
        ▼
POST /audio/ingest (multipart: business_id, conv_id, file)
        │
        ├─► AudioRepository.save_audio(conv_id, bytes)
        │       └─► Fernet.encrypt(bytes) → data/audio/{conv_id}.bin
        │
        ├─► transcribe_audio(business_id, conv_id, audio_bytes)
        │       ├─► pii_redaction.redact_text() on raw payload
        │       ├─► rapidapi_whisper_transcribe()   [primary]
        │       │       └─► POST speech-to-text-ai.p.rapidapi.com
        │       └─► whisper_transcribe()             [fallback]
        │               └─► OpenAI Whisper-1
        │
        └─► AudioRepository.save_transcript(conv_id, segments)
                └─► In-memory dict cache

Response: {"status": "accepted", "conv_id": "..."}
```

### 6.2 Voice Chat Turn Flow

```
Client sends user utterance
        │
        ▼
POST /audio/voice/chat
{conv_id, business_id, message, history, first_turn}
        │
        ├─[first_turn=true]─► Return greeting immediately (no LLM call)
        │                      Store _opencode_sessions[conv_id]
        │
        ├─[already escalated]─► Return "hold the line" message
        │
        └─[normal turn]
                │
                ├─► get_business_name(business_id)   ← reads data/users.json
                ├─► load_business_context(business_id) ← reads data/contexts/{biz}/
                ├─► list_active_rules(business_id)    ← reads data/escalations/{biz}/rules.json
                │
                ├─► Build system prompt with:
                │     - Business name + context
                │     - Escalation rules (numbered list)
                │
                ├─► GET/CREATE OpenCode session (POST localhost:4096/session)
                │     └─► Inject system prompt (noReply=true)
                │
                ├─► POST localhost:4096/session/{id}/message
                │     └─► Get LLM reply
                │
                ├─► _run_tool_decision(llm_adapter_url, history, reply)
                │     └─► POST localhost:9100/v1/generate
                │           with ESCALATION_TOOL_SCHEMA
                │           └─► Returns tool_args or None
                │                (keyword fallback if no tool call)
                │
                ├─[escalation detected]
                │     ├─► create_ticket_internal(...)
                │     ├─► broadcast_ticket(ticket) → all SSE subscribers
                │     ├─► _opencode_sessions[conv_id].escalated = True
                │     └─► Return {reply, history, escalated: true}
                │
                └─[no escalation]
                      └─► Return {reply, history, escalated: false}
```

### 6.3 Human Agent Dashboard Flow (SSE)

```
Human agent dashboard connects
        │
        ▼
GET /escalation-queue/stream?token=<jwt>
        │
        ├─► Validate JWT (no Authorization header — query param only)
        ├─► Create asyncio.Queue (maxsize=50)
        ├─► Append to _sse_subscribers list
        └─► StreamingResponse (text/event-stream)
              │
              ├─ Sends "data: connected\n\n" immediately
              ├─ Waits for queue items (30s timeout → keepalive ping)
              └─ Each ticket: "data: {ticket_json}\n\n"

When voice/chat escalates a call:
  broadcast_ticket(ticket_dict)
        └─► put_nowait(ticket_dict) into every subscriber queue
                └─► All connected dashboards instantly receive the ticket
```

---

## 7. API Endpoints

### Authentication requirements

- **Public** — no token needed
- **Bearer** — requires `Authorization: Bearer <token>` header
- **SSE token** — requires `?token=<jwt>` query parameter

---

### 7.1 Health

#### `GET /health`

Check API liveness.

- **Auth:** Public
- **Response:** `200 OK`

```json
{"status": "ok", "version": "0.1.0"}
```

**Example:**
```bash
curl http://localhost:8000/health
```

---

### 7.2 Authentication

#### `POST /auth/register`

Register a new business account. Returns a JWT on success.

- **Auth:** Public
- **Response:** `201 Created`

**Request body:**
```json
{
  "username": "alice",
  "email": "alice@example.com",
  "password": "strongpass123",
  "business_name": "Alice Corp"
}
```

| Field | Type | Required | Validation |
|-------|------|----------|-----------|
| `username` | string | Yes | ≥ 3 chars, alphanumeric + `-_` only |
| `email` | string | Yes | Any string (no format check server-side) |
| `password` | string | Yes | ≥ 8 characters |
| `business_name` | string | No | Falls back to username if blank |

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "business_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "alice",
  "business_name": "Alice Corp"
}
```

**Error responses:**
- `409 Conflict` — username already taken
- `422 Unprocessable Entity` — validation failure

**Example:**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@acme.com","password":"secret123","business_name":"Acme Inc"}'
```

---

#### `POST /auth/login`

Authenticate an existing user.

- **Auth:** Public
- **Response:** `200 OK`

**Request body:**
```json
{
  "username": "alice",
  "password": "secret123"
}
```

**Response:** Same as `/auth/register` response (TokenResponse)

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "business_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "alice",
  "business_name": "Acme Inc"
}
```

**Error responses:**
- `401 Unauthorized` — invalid username or password

**Example:**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"secret123"}'
```

---

#### `GET /auth/me`

Return the currently authenticated user's profile.

- **Auth:** Bearer
- **Response:** `200 OK`

**Response:**
```json
{
  "id": "user-uuid",
  "username": "alice",
  "email": "alice@acme.com",
  "business_id": "biz-uuid",
  "business_name": "Acme Inc",
  "created_at": "2025-01-15T10:00:00+00:00"
}
```

**Example:**
```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer eyJhbGci..."
```

---

### 7.3 Audio Ingest & Transcripts

#### `POST /audio/ingest`

Upload a raw audio file for a call. The backend encrypts the audio, transcribes it (RapidAPI Whisper → OpenAI Whisper fallback), and stores the transcript.

- **Auth:** Public (no token required)
- **Content-Type:** `multipart/form-data`
- **Response:** `202 Accepted`

**Form fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `business_id` | string | Yes | Tenant identifier UUID |
| `conv_id` | string | Yes | Conversation/call identifier |
| `file` | binary | Yes | Audio file (webm, wav, mp3, etc.) |

**Response:**
```json
{
  "status": "accepted",
  "conv_id": "call-abc-123"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/audio/ingest \
  -F "business_id=biz-uuid" \
  -F "conv_id=call-001" \
  -F "file=@recording.webm"
```

---

#### `GET /audio/transcript/{conv_id}`

Retrieve the transcript segments for a conversation. Transcripts are held in memory (lost on server restart).

- **Auth:** Public
- **Response:** `200 OK` — array of `TranscriptSegment`

**Path parameter:** `conv_id` — conversation identifier

**Response:**
```json
[
  {
    "business_id": "biz-uuid",
    "conv_id": "call-001",
    "segment_id": "call-001-0",
    "speaker": "customer",
    "start_ts": "2025-01-15T10:00:00+00:00",
    "end_ts": "2025-01-15T10:00:05+00:00",
    "text": "Hello, I need help with my account.",
    "confidence": 0.95
  },
  {
    "business_id": "biz-uuid",
    "conv_id": "call-001",
    "segment_id": "call-001-1",
    "speaker": "agent",
    "start_ts": "2025-01-15T10:00:05+00:00",
    "end_ts": "2025-01-15T10:00:10+00:00",
    "text": "Of course! Let me pull up your account.",
    "confidence": 0.98
  }
]
```

**Error responses:**
- `404 Not Found` — conversation not found in transcript cache

**Example:**
```bash
curl http://localhost:8000/audio/transcript/call-001
```

---

#### `POST /audio/simulate`

Inject a text script as a transcript (for demo/testing purposes without real audio).

- **Auth:** Public
- **Response:** `200 OK`

**Request body:**
```json
{
  "business_id": "biz-uuid",
  "conv_id": "demo-call-001",
  "script": "Customer: I need to cancel my subscription.\nAgent: I can help you with that."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `business_id` | string | Yes | Tenant identifier |
| `conv_id` | string | Yes | Conversation identifier |
| `script` | string | Yes | Multi-line text. Each line: `Speaker: Text` |

**Script parsing rules:**
- Lines matching `Speaker: Text` are parsed into segments
- Blank lines are skipped
- Speaker classification: contains "agent" → `"agent"`, contains "customer" or "caller" → `"customer"`, else `null`
- Timestamps start from `now`, each segment 5 seconds apart

**Response:**
```json
{
  "status": "accepted",
  "conv_id": "demo-call-001",
  "segments": 2
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/audio/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "business_id": "biz-uuid",
    "conv_id": "demo-001",
    "script": "Customer: My internet is down.\nAgent: Let me check your connection.\nCustomer: It has been down for 3 hours."
  }'
```

---

### 7.4 Voice / LLM Conversation

#### `POST /audio/voice/chat`

Send a message in an AI voice conversation. The backend manages OpenCode sessions, builds the system prompt from business context and rules, runs escalation detection, and returns the LLM reply.

- **Auth:** Public (business_id is passed in body)
- **Response:** `200 OK`

**Request body:**
```json
{
  "conv_id": "call-uuid-001",
  "business_id": "biz-uuid",
  "message": "I want to speak to a manager",
  "history": [
    {"role": "assistant", "content": "Hello, this is Acme Inc, how may I assist you today?"},
    {"role": "user", "content": "My order arrived broken."}
  ],
  "first_turn": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `conv_id` | string | Yes | Unique conversation/call ID |
| `business_id` | string | Yes | Tenant identifier |
| `message` | string | No | User's utterance (empty on first turn) |
| `history` | array | No | Previous `{role, content}` messages |
| `first_turn` | bool | No | If `true`, returns greeting without LLM call |

**Response (normal turn):**
```json
{
  "reply": "I understand your frustration. Let me connect you with a specialist right away.",
  "history": [
    {"role": "assistant", "content": "Hello, this is Acme Inc..."},
    {"role": "user", "content": "My order arrived broken."},
    {"role": "user", "content": "I want to speak to a manager"},
    {"role": "assistant", "content": "I understand your frustration..."}
  ],
  "escalated": false
}
```

**Response (escalation triggered):**
```json
{
  "reply": "I've opened a support ticket for you. A human agent will be with you shortly — please hold the line.",
  "history": [...],
  "escalated": true
}
```

**Response (first_turn=true):**
```json
{
  "reply": "Hello, this is Acme Inc, how may I assist you today?",
  "history": [{"role": "assistant", "content": "Hello, this is Acme Inc, how may I assist you today?"}],
  "escalated": false
}
```

**Error responses:**
- `502 Bad Gateway` — OpenCode server unavailable or error

**Escalation detection logic (two-layer):**
1. **LLM tool-calling** — after getting the reply, sends the conversation + reply to `POST localhost:9100/v1/generate` with a `create_escalation_ticket` tool schema. If the LLM returns a tool call, a ticket is created.
2. **Keyword fallback** — if LLM adapter returns no tool call, checks the reply for phrases like "human agent", "live agent", "please hold", "connecting you", etc.
3. **XML marker fallback** — detects `<escalate reason="..." priority="..." rule="..."/>` in the raw reply.

**Example:**
```bash
# First turn
curl -X POST http://localhost:8000/audio/voice/chat \
  -H "Content-Type: application/json" \
  -d '{"conv_id":"call-001","business_id":"biz-uuid","first_turn":true}'

# Subsequent turn
curl -X POST http://localhost:8000/audio/voice/chat \
  -H "Content-Type: application/json" \
  -d '{
    "conv_id": "call-001",
    "business_id": "biz-uuid",
    "message": "I want to cancel my account",
    "history": [{"role":"assistant","content":"Hello, how can I help?"}],
    "first_turn": false
  }'
```

---

#### `POST /audio/voice/tts`

Convert text to speech (MP3 audio) using OpenAI TTS.

- **Auth:** Public
- **Response:** `200 OK` — binary `audio/mpeg`

**Request body:**
```json
{
  "text": "Hello, this is Acme Inc, how may I assist you today?",
  "voice": "alloy"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | Yes | Text to synthesise |
| `voice` | string | No | OpenAI voice name. Default: `"alloy"`. Options: `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer` |

**Response:** Raw MP3 bytes (`Content-Type: audio/mpeg`)

**Error responses:**
- `503 Service Unavailable` — `OPENAI_API_KEY` not set or openai package not installed
- `502 Bad Gateway` — OpenAI API error

**Example:**
```bash
curl -X POST http://localhost:8000/audio/voice/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"Thank you for calling.","voice":"nova"}' \
  --output response.mp3
```

---

#### `POST /audio/voice/stt`

Transcribe an audio file to text. Tries RapidAPI Whisper first, falls back to OpenAI Whisper.

- **Auth:** Public
- **Content-Type:** `multipart/form-data`
- **Response:** `200 OK`

**Form field:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | binary | Yes | Audio file (webm, wav, mp3, ogg, etc.) |

**Response:**
```json
{
  "text": "I need help with my recent order number 12345."
}
```

Empty audio (< 100 bytes) returns `{"text": ""}`.

**Provider selection:**
- If `CALLSUP_AUDIO_ENGINE_RAPIDAPI_WHISPER_KEY` is set → RapidAPI Whisper (primary)
- Codec suffix stripped from Content-Type (e.g. `audio/webm;codecs=opus` → `audio/webm`)
- Falls back to OpenAI Whisper-1 if RapidAPI fails or returns empty text
- Falls back to mock transcriber if OpenAI key is not set

**Example:**
```bash
curl -X POST http://localhost:8000/audio/voice/stt \
  -F "file=@utterance.webm"
```

---

### 7.5 Escalation Queue

Manages support tickets created when a call is escalated to a human agent.

#### `GET /escalation-queue/stream`

Real-time SSE stream. Connected dashboards receive new tickets instantly as they are created.

- **Auth:** JWT passed as query parameter `?token=<jwt>` (not Authorization header)
- **Response:** `text/event-stream` (persistent connection)

**Query parameter:** `token` — valid JWT access token

**Event format:**
```
data: connected

: keepalive

data: {"id":"ticket-uuid","business_id":"...","conv_id":"...","session_id":"...","reason":"...","priority":"medium","summary":null,"rule_triggered":null,"status":"pending","created_at":"...","claimed_by":null,"resolved_at":null,"conversation_history":[...]}

```

- Sends `data: connected` immediately on connect
- Sends `: keepalive` every 30 seconds to keep the connection alive
- Each new escalation ticket is sent as `data: {json}\n\n`

**Example (JavaScript):**
```javascript
const token = localStorage.getItem('access_token');
const source = new EventSource(`http://localhost:8000/escalation-queue/stream?token=${token}`);
source.onmessage = (event) => {
  if (event.data === 'connected') return;
  const ticket = JSON.parse(event.data);
  console.log('New ticket:', ticket);
};
```

---

#### `GET /escalation-queue`

List all escalation tickets for the authenticated business.

- **Auth:** Bearer
- **Response:** `200 OK` — array of `EscalationTicket` (newest first)

**Query parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `status` | string | No | Filter by status: `pending`, `claimed`, or `resolved` |

**Response:**
```json
[
  {
    "id": "ticket-uuid",
    "business_id": "biz-uuid",
    "conv_id": "call-001",
    "session_id": "call-001",
    "reason": "Customer requested to speak with a manager",
    "priority": "high",
    "summary": null,
    "rule_triggered": null,
    "status": "pending",
    "created_at": "2025-01-15T10:15:00+00:00",
    "claimed_by": null,
    "resolved_at": null,
    "conversation_history": [
      {"role": "assistant", "content": "Hello, how can I help?"},
      {"role": "user", "content": "I want to speak to a manager"}
    ]
  }
]
```

**Example:**
```bash
# All tickets
curl http://localhost:8000/escalation-queue \
  -H "Authorization: Bearer eyJhbGci..."

# Only pending
curl "http://localhost:8000/escalation-queue?status=pending" \
  -H "Authorization: Bearer eyJhbGci..."
```

---

#### `GET /escalation-queue/{ticket_id}`

Get a single escalation ticket by ID.

- **Auth:** Bearer
- **Response:** `200 OK` — `EscalationTicket`

**Error responses:**
- `404 Not Found` — ticket not found

**Example:**
```bash
curl http://localhost:8000/escalation-queue/ticket-uuid \
  -H "Authorization: Bearer eyJhbGci..."
```

---

#### `POST /escalation-queue`

Manually create an escalation ticket (human agents or automated systems).

- **Auth:** Bearer
- **Response:** `201 Created`

**Request body:**
```json
{
  "session_id": "call-001",
  "reason": "Customer threatening to cancel high-value contract",
  "priority": "high",
  "rule_triggered": "rule-uuid",
  "conv_id": "call-001",
  "summary": "VIP customer with billing dispute"
}
```

| Field | Type | Required | Validation |
|-------|------|----------|-----------|
| `session_id` | string | Yes | — |
| `reason` | string | Yes | — |
| `priority` | string | No | `high`, `medium`, or `low`. Default: `medium` |
| `rule_triggered` | string | No | Rule UUID that triggered this |
| `conv_id` | string | No | — |
| `summary` | string | No | — |

**Response:** Full `EscalationTicket` object (see above)

**Error responses:**
- `422 Unprocessable Entity` — invalid priority value

**Example:**
```bash
curl -X POST http://localhost:8000/escalation-queue \
  -H "Authorization: Bearer eyJhbGci..." \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "call-001",
    "reason": "Customer needs billing refund approval",
    "priority": "high",
    "conv_id": "call-001"
  }'
```

---

#### `PUT /escalation-queue/{ticket_id}`

Update a ticket's status (claim or resolve it).

- **Auth:** Bearer
- **Response:** `200 OK` — updated `EscalationTicket`

**Request body:**
```json
{
  "status": "claimed",
  "claimed_by": "agent-jane"
}
```

| Field | Type | Required | Validation |
|-------|------|----------|-----------|
| `status` | string | Yes | `pending`, `claimed`, or `resolved` |
| `claimed_by` | string | No | Agent's username |

**Behaviour:**
- Setting `status: "resolved"` automatically sets `resolved_at` to current UTC timestamp

**Error responses:**
- `404 Not Found` — ticket not found
- `422 Unprocessable Entity` — invalid status value

**Example:**
```bash
# Claim a ticket
curl -X PUT http://localhost:8000/escalation-queue/ticket-uuid \
  -H "Authorization: Bearer eyJhbGci..." \
  -H "Content-Type: application/json" \
  -d '{"status":"claimed","claimed_by":"agent-jane"}'

# Resolve a ticket
curl -X PUT http://localhost:8000/escalation-queue/ticket-uuid \
  -H "Authorization: Bearer eyJhbGci..." \
  -H "Content-Type: application/json" \
  -d '{"status":"resolved"}'
```

---

### 7.6 Escalation Rules

Rules define when the AI should escalate a call to a human agent. Active rules are injected into the LLM system prompt on every voice/chat turn.

#### `GET /escalation-rules`

List all escalation rules for the authenticated business.

- **Auth:** Bearer
- **Response:** `200 OK` — array of `EscalationRule`

**Response:**
```json
[
  {
    "id": "rule-uuid",
    "business_id": "biz-uuid",
    "rule_text": "Escalate if customer mentions a refund over $500",
    "ai_refined_text": "If the customer requests a refund exceeding $500, escalate the call immediately to a senior agent.",
    "priority": "high",
    "is_active": true,
    "created_at": "2025-01-10T09:00:00+00:00",
    "updated_at": "2025-01-10T09:00:00+00:00"
  }
]
```

**Example:**
```bash
curl http://localhost:8000/escalation-rules \
  -H "Authorization: Bearer eyJhbGci..."
```

---

#### `POST /escalation-rules`

Create a new escalation rule.

- **Auth:** Bearer
- **Response:** `201 Created`

**Request body:**
```json
{
  "rule_text": "Escalate if customer mentions a refund over $500",
  "priority": "high",
  "refine_with_ai": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `rule_text` | string | Yes | Human-authored escalation condition |
| `priority` | string | No | `high`, `medium`, or `low`. Default: `medium` |
| `refine_with_ai` | bool | No | If `true`, rewrites rule via LLM adapter for clarity. Default: `false` |

**When `refine_with_ai: true`:** sends the rule to `POST localhost:9100/v1/generate` with a rewrite prompt. The improved version is stored in `ai_refined_text` and is what gets injected into the LLM system prompt.

**Response:** Full `EscalationRule` object

**Example:**
```bash
curl -X POST http://localhost:8000/escalation-rules \
  -H "Authorization: Bearer eyJhbGci..." \
  -H "Content-Type: application/json" \
  -d '{
    "rule_text": "Transfer to human if customer is very angry",
    "priority": "high",
    "refine_with_ai": true
  }'
```

---

#### `PUT /escalation-rules/{rule_id}`

Update an existing escalation rule.

- **Auth:** Bearer
- **Response:** `200 OK` — updated `EscalationRule`

**Request body (all fields optional):**
```json
{
  "rule_text": "Escalate if customer mentions account cancellation",
  "ai_refined_text": "If the customer expresses intent to cancel their account, immediately escalate to a retention specialist.",
  "priority": "high",
  "is_active": true,
  "refine_with_ai": false
}
```

| Field | Type | Description |
|-------|------|-------------|
| `rule_text` | string | New human-authored rule text |
| `ai_refined_text` | string | Manually override the AI-refined version |
| `priority` | string | `high`, `medium`, or `low` |
| `is_active` | bool | Enable or disable the rule |
| `refine_with_ai` | bool | If `true`, re-runs LLM refinement on the current rule_text |

**Error responses:**
- `404 Not Found` — rule not found

**Example:**
```bash
curl -X PUT http://localhost:8000/escalation-rules/rule-uuid \
  -H "Authorization: Bearer eyJhbGci..." \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

---

#### `DELETE /escalation-rules/{rule_id}`

Delete an escalation rule.

- **Auth:** Bearer
- **Response:** `204 No Content`

**Error responses:**
- `404 Not Found` — rule not found

**Example:**
```bash
curl -X DELETE http://localhost:8000/escalation-rules/rule-uuid \
  -H "Authorization: Bearer eyJhbGci..."
```

---

### 7.7 Business Context

Context items are Markdown documents stored per business. They are assembled into the LLM system prompt on every voice/chat turn so the AI knows about the business. Alerts appear under a prominent `## ACTIVE ALERTS` section; regular items appear under `## BUSINESS INFORMATION`.

#### `GET /context`

List all context items for the authenticated business.

- **Auth:** Bearer
- **Response:** `200 OK` — array of `ContextItem`

**Response:**
```json
[
  {
    "id": "ctx-uuid",
    "label": "Return Policy",
    "type": "manual",
    "file_name": null,
    "is_alert": false,
    "expires_at": null,
    "created_at": "2025-01-10T08:00:00+00:00",
    "updated_at": "2025-01-10T08:00:00+00:00",
    "content": "## Return Policy\n\nCustomers may return products within 30 days..."
  }
]
```

**Example:**
```bash
curl http://localhost:8000/context \
  -H "Authorization: Bearer eyJhbGci..."
```

---

#### `POST /context`

Create a new context document.

- **Auth:** Bearer
- **Response:** `201 Created`

**Request body:**
```json
{
  "label": "System Outage Alert",
  "content": "Our payment processing system is currently down. Do not promise same-day transactions.",
  "type": "manual",
  "file_name": null,
  "refine_with_ai": false,
  "is_alert": true,
  "expires_at": "2025-01-16T18:00:00+00:00"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `label` | string | Yes | Display name for this context item |
| `content` | string | Yes | Markdown content body |
| `type` | string | No | `"manual"` or `"file"`. Default: `"manual"` |
| `file_name` | string | No | Original file name if uploaded as a file |
| `refine_with_ai` | bool | No | If `true`, rewrites content via LLM for clarity |
| `is_alert` | bool | No | If `true`, appears under `ACTIVE ALERTS` in the LLM prompt |
| `expires_at` | string | No | ISO-8601 UTC. After this time, the item is excluded from prompts |

**Response:** Full `ContextItem` object

**Example:**
```bash
curl -X POST http://localhost:8000/context \
  -H "Authorization: Bearer eyJhbGci..." \
  -H "Content-Type: application/json" \
  -d '{
    "label": "Holiday Hours",
    "content": "We are closed on December 25th and January 1st.",
    "is_alert": false
  }'
```

---

#### `PUT /context/{item_id}`

Update an existing context item.

- **Auth:** Bearer
- **Response:** `200 OK` — updated `ContextItem`

**Request body (all fields optional):**
```json
{
  "label": "Updated Return Policy",
  "content": "Customers may return products within 60 days for full refund.",
  "refine_with_ai": false,
  "is_alert": false,
  "expires_at": null
}
```

**Error responses:**
- `404 Not Found` — item not found

**Example:**
```bash
curl -X PUT http://localhost:8000/context/ctx-uuid \
  -H "Authorization: Bearer eyJhbGci..." \
  -H "Content-Type: application/json" \
  -d '{"label": "New Label", "content": "Updated content."}'
```

---

#### `DELETE /context/{item_id}`

Delete a context item.

- **Auth:** Bearer
- **Response:** `204 No Content`

**Error responses:**
- `404 Not Found` — item not found

**Example:**
```bash
curl -X DELETE http://localhost:8000/context/ctx-uuid \
  -H "Authorization: Bearer eyJhbGci..."
```

---

### 7.8 Metrics

#### `GET /metrics`

Prometheus metrics endpoint. Returns metrics in Prometheus text exposition format.

- **Auth:** Public
- **Response:** `200 OK` — Prometheus text format

**Metrics exposed:**

| Metric | Type | Description |
|--------|------|-------------|
| `callsup_audio_ingest_requests_total` | Counter | Total audio ingest requests |
| `callsup_audio_transcript_requests_total` | Counter | Total transcript fetch requests |
| `callsup_audio_ingest_processing_seconds` | Histogram | Time spent processing ingest requests |

**Example:**
```bash
curl http://localhost:8000/metrics
```

---

## 8. Escalation Lifecycle

```
                    [CALL STARTS]
                         │
                         ▼
               POST /audio/voice/chat
                   first_turn: true
                         │
                         ▼
                  AI greets caller
                 (no LLM call yet)
                         │
                    [CONVERSATION]
                         │
                         ▼
               POST /audio/voice/chat
                  (each utterance)
                         │
               ┌─────────┴──────────┐
               │                    │
         LLM gives reply      Already escalated?
               │                    │
               ▼                    ▼
    _run_tool_decision()     "Please hold..."
    POST :9100/v1/generate   escalated: true
               │
    ┌──────────┴───────────────┐
    │                          │
  Tool call              No tool call
  returned?              │
    │                    ▼
    │         Keyword check in reply
    │         ("human agent", "please hold", etc.)
    │                    │
    ├────────────────────┘
    │
    ▼
  ESCALATION TRIGGERED
    │
    ├─► create_ticket_internal()
    │     └─► Write to data/escalations/{biz}/queue.json
    │
    ├─► broadcast_ticket()
    │     └─► All SSE subscribers receive ticket instantly
    │
    ├─► _opencode_sessions[conv_id].escalated = True
    │     └─► Future turns short-circuit to "please hold"
    │
    └─► Return {reply, history, escalated: true}

[HUMAN AGENT DASHBOARD]
    │
    ├─► GET /escalation-queue/stream  (SSE)
    │     └─► Receives ticket in real-time
    │
    ├─► PUT /escalation-queue/{id}
    │     body: {"status": "claimed", "claimed_by": "agent-jane"}
    │
    └─► PUT /escalation-queue/{id}
          body: {"status": "resolved"}
          └─► resolved_at timestamp set automatically
```

**Ticket status transitions:**
```
pending → claimed → resolved
```

---

## 9. Storage Layer

### 9.1 File Layout

```
data/
├── users.json                           # All registered users (all tenants)
├── audio/
│   └── {conv_id}.bin                   # Fernet-encrypted audio bytes
├── escalations/
│   └── {business_id}/
│       ├── queue.json                  # Array of EscalationTicket objects
│       └── rules.json                  # Array of EscalationRule objects
└── contexts/
    └── {business_id}/
        ├── index.json                  # Array of ContextItemMeta objects
        └── {item_id}.md               # Markdown content for each context item
```

### 9.2 Audio Encryption

Audio files are encrypted using **Fernet** symmetric encryption:

- The key is derived at startup from `CALLSUP_AUDIO_ENGINE_ENCRYPTION_KEY`
- If the key is not a valid Fernet key, it is SHA-256 hashed and base64url-encoded to produce a valid 32-byte key
- Encrypted files are stored as `.bin` files in `data/audio/`
- Transcripts are **NOT** persisted — they live in-memory only and are lost on server restart

### 9.3 Transcript In-Memory Cache

```python
# AudioRepository._transcripts: dict[str, list[TranscriptSegment]]
# Key: conv_id
# Value: list of TranscriptSegment objects
```

> **Note:** Transcripts are not persisted to disk. A server restart clears all cached transcripts. Production deployments should add a persistent transcript store.

---

## 10. External Services

### 10.1 OpenCode Server (`localhost:4096`)

Manages stateful LLM conversation sessions.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/session` | POST | Create a new session |
| `/session/{id}/message` | POST | Send a message and get a reply |

**Session creation:**
```json
POST /session
{"title": "callsup-{conv_id}"}

Response: {"id": "session-uuid", ...}
```

**System prompt injection (silent, no AI reply):**
```json
POST /session/{id}/message
{"noReply": true, "parts": [{"type": "text", "text": "<system prompt>"}]}
```

**Conversation turn:**
```json
POST /session/{id}/message
{"parts": [{"type": "text", "text": "user utterance"}]}

Response: {"parts": [{"type": "text", "text": "AI reply"}], ...}
```

Sessions are stored in `_opencode_sessions: dict[str, dict]` in memory (keyed by `conv_id`).

### 10.2 LLM Adapter (`localhost:9100`)

Used for two purposes:
1. **Escalation tool-calling** — decides if a call should be escalated
2. **Rule/context refinement** — rewrites human-authored text for LLM clarity

**Endpoint:** `POST /v1/generate`

**Request (escalation decision):**
```json
{
  "model": "gpt-4.1-mini",
  "messages": [...conversation history...],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "create_escalation_ticket",
        "description": "Call this function when the AI agent has decided to escalate...",
        "parameters": {
          "type": "object",
          "properties": {
            "reason": {"type": "string"},
            "priority": {"enum": ["high", "medium", "low"]},
            "rule_triggered": {"type": "string"}
          },
          "required": ["reason", "priority"]
        }
      }
    }
  ],
  "tool_choice": "auto"
}
```

**Response (escalation):**
```json
{
  "tool_calls": [
    {
      "function": {
        "name": "create_escalation_ticket",
        "arguments": "{\"reason\": \"...\", \"priority\": \"high\"}"
      }
    }
  ]
}
```

**Response (no escalation):**
```json
{"tool_calls": []}
```

**The `svc_llm_adapter.py` file in the repo is a mock adapter** for local testing — it returns canned responses without calling a real LLM.

### 10.3 RapidAPI Whisper STT

- **URL:** configured via `CALLSUP_AUDIO_ENGINE_RAPIDAPI_WHISPER_URL`
- **Default host:** `speech-to-text-ai.p.rapidapi.com`
- Multipart POST with `file`, `lang`, and `task=transcribe` params
- Response formats: `{"results": [{"transcript": "..."}]}` or `{"text": "..."}`

### 10.4 OpenAI API

Used for:
1. **STT fallback** — `client.audio.transcriptions.create(model="whisper-1", response_format="verbose_json")`
2. **TTS** — `client.audio.speech.create(model="tts-1", voice=..., input=...)`

---

## 11. PII Redaction

The `pii_redaction.py` module scrubs sensitive data from text before external processing.

**Patterns detected and replaced:**

| Pattern | Replacement |
|---------|-------------|
| Email addresses | `[REDACTED_EMAIL]` |
| US phone numbers (various formats) | `[REDACTED_PHONE]` |
| Social Security Numbers (`XXX-XX-XXXX`) | `[REDACTED_SSN]` |
| Credit/debit card numbers (13–19 digits) | `[REDACTED_CARD]` |

**Usage in transcription pipeline:** `redact_text()` is called on the raw audio payload text representation before sending to the mock third-party transcriber (the RapidAPI and OpenAI paths use binary audio directly and do not pass through redaction).

---

## 12. Environment Variables Reference

All variables are prefixed with `CALLSUP_AUDIO_ENGINE_` when set in `.env`.

| Variable | Default | Description |
|----------|---------|-------------|
| `CALLSUP_AUDIO_ENGINE_SERVICE_VERSION` | `"0.1.0"` | API version string returned in `/health` |
| `CALLSUP_AUDIO_ENGINE_LOG_LEVEL` | `"INFO"` | Python log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `CALLSUP_AUDIO_ENGINE_DATA_DIR` | `"data"` | Root directory for all file storage |
| `CALLSUP_AUDIO_ENGINE_ENCRYPTION_KEY` | — | Fernet encryption key for audio files (or raw string → SHA-256 derived) |
| `CALLSUP_AUDIO_ENGINE_OPENAI_API_KEY` | — | OpenAI API key for Whisper STT + TTS |
| `CALLSUP_AUDIO_ENGINE_RAPIDAPI_WHISPER_KEY` | — | RapidAPI key for Whisper STT (primary STT provider) |
| `CALLSUP_AUDIO_ENGINE_RAPIDAPI_WHISPER_HOST` | — | RapidAPI Whisper host header |
| `CALLSUP_AUDIO_ENGINE_RAPIDAPI_WHISPER_URL` | — | Full URL for RapidAPI Whisper endpoint |
| `CALLSUP_AUDIO_ENGINE_RAPIDAPI_WHISPER_LANG` | — | Language code (e.g. `"en"`) |
| `CALLSUP_AUDIO_ENGINE_ENFORCE_TLS_IN_TRANSIT` | `true` | Reject HTTP requests (require HTTPS) |
| `CALLSUP_AUDIO_ENGINE_ALLOW_INSECURE_HTTP` | `false` | Override TLS enforcement for local dev |
| `CALLSUP_AUDIO_ENGINE_JWT_SECRET` | `"callsup-dev-secret-change-in-production"` | **Change in production!** HS256 signing secret |
| `CALLSUP_AUDIO_ENGINE_JWT_ALGORITHM` | `"HS256"` | JWT signing algorithm |
| `CALLSUP_AUDIO_ENGINE_JWT_EXPIRE_HOURS` | `24` | JWT expiry in hours |
| `CALLSUP_AUDIO_ENGINE_LLM_ADAPTER_URL` | `"http://127.0.0.1:9100"` | LLM adapter service base URL |
| `CALLSUP_AUDIO_ENGINE_VAULT_API_KEY_REF` | — | HashiCorp Vault path for API key secret |
| `CALLSUP_AUDIO_ENGINE_VAULT_ENCRYPTION_KEY_REF` | — | HashiCorp Vault path for encryption key secret |
| `OPENCODE_SERVER_URL` | `"http://127.0.0.1:4096"` | OpenCode LLM server URL (read directly from `os.environ`) |
| `OPENAI_API_KEY` | — | Also read directly from `os.environ` for TTS/STT |

> **Security note:** Always set `CALLSUP_AUDIO_ENGINE_JWT_SECRET` to a strong random value in production. The default value is publicly known and must not be used in any non-development environment.

---

## 13. Security Controls

| Control | Implementation |
|---------|---------------|
| **Authentication** | JWT Bearer tokens, HS256 signed, 24hr expiry |
| **Password hashing** | SHA-256 with per-user 16-byte random salt |
| **Password comparison** | `secrets.compare_digest()` (constant-time, prevents timing attacks) |
| **Audio encryption** | Fernet symmetric encryption at rest |
| **TLS enforcement** | Middleware rejects non-HTTPS requests (configurable) |
| **HSTS** | `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload` |
| **Clickjacking protection** | `X-Frame-Options: DENY` |
| **MIME sniffing protection** | `X-Content-Type-Options: nosniff` |
| **CORS** | Restricted to `localhost:5173` and `localhost:8081` |
| **PII redaction** | Email, phone, SSN, card numbers scrubbed before external processing |
| **Input validation** | Pydantic v2 with `extra="forbid"` on all models |
| **Extra field rejection** | `model_config = ConfigDict(extra="forbid")` rejects unknown fields |
| **SSE authentication** | JWT validated via `?token=` query parameter before stream opens |

---

*Generated from source code analysis of the CALLSUP Audio Engine backend.*
