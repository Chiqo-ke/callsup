# CALLSUP

AI-powered call-support platform. Transcribes calls, detects intent, generates actions, and escalates conversations that need human intervention.

## Architecture

```
callsup-web/           React 19 + TypeScript dashboard (frontend)
consolidated/
  callsup-platform/            Platform service
  callsup-audio-engine/        Whisper transcription  · port 8010
  callsup-intelligence-engine/ NLU + action engine    · port 8011
svc-llm-adapter/               GitHub Copilot proxy   · port 9100
callsup-specs/                 OpenAPI contracts + governance
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Audio Engine | 8010 | Ingest audio, redact PII, retrieve transcripts |
| Intelligence Engine | 8011 | Intent detection, action decisions, escalation |
| LLM Adapter | 9100 | Authenticated GitHub Copilot / OpenAI proxy |

## Web Dashboard

Located at `callsup-web/`. Features:
- **Live service health** — online/offline status and version per service
- **Analytics stats** — pending escalation tickets, resolved today, total escalations, services online
- **Task queue** — escalated conversations that require human intervention, with one-click Resolve
- **Audio ingest** — upload recordings for transcription
- **Transcripts** — browse conversation segments with PII redacted
- **Intelligence** — step-by-step analysis tool
- **Call simulation** — test the full pipeline with a scripted conversation
- **Context management** — manage business knowledge used by the intelligence engine

## Quick Start

See [RUNNING_THE_SYSTEM.md](RUNNING_THE_SYSTEM.md) for full instructions.

```powershell
# 1. Start backend services (3 terminals — see RUNNING_THE_SYSTEM.md)

# 2. Start frontend
Set-Location callsup-web
npm install
npm run dev   # http://localhost:5173
```

## Security

- PII is redacted before any third-party LLM call (phone, email, SSN, card numbers)
- Audio encrypted at rest with Fernet
- TLS enforced in transit (configurable per service)
- Raw service URLs are never exposed in the frontend UI

## Tests

```powershell
# Backend smoke test (requires all 3 services running)
& "C:\Users\nyaga\Documents\.venv\Scripts\python.exe" smoke_test.py

# Module unit tests — see PROJECT_STATUS_SUMMARY.md § 3
```
