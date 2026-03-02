# CALLSUP Intelligence Engine (v0.1.0)

FastAPI service for the CALLSUP Intelligence Engine with mandatory redaction before LLM calls, `svc-llm-adapter` local contract integration, LLM audit records, transactional response verification, structured conversation logs, health/readiness/metrics endpoints, and mocked integration tests.

## Layout

```text
src/
  callsup_intelligence_engine/
    api/
    core/
    tests/
openapi.yaml
resources.json
Dockerfile
scripts/e2e_demo.py
callsup-specs/intelligence_engine/openapi.yaml
callsup-specs/intelligence_engine/resources.json
```

## Quickstart

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -e .[dev]
pytest
uvicorn callsup_intelligence_engine.main:app --host 0.0.0.0 --port 8000
```

## API

- `GET /health`
- `GET /readiness`
- `GET /metrics`
- `POST /intelligence/step`
- `POST /intelligence/e2e-demo`

Example `POST /intelligence/step` payload:

```json
{
  "business_id": "biz-001",
  "conv_id": "conv-123",
  "segment": {
    "event": "transcript.segment",
    "business_id": "biz-001",
    "conv_id": "conv-123",
    "segment_id": "seg-1",
    "speaker": "customer",
    "start_ts": "2026-01-01T00:00:00Z",
    "end_ts": "2026-01-01T00:00:03Z",
    "text": "My email is test@example.com and what is my balance?",
    "confidence": 0.95
  },
  "session_state": {}
}
```

## Security and LLM controls

- PII redaction is mandatory before every LLM prompt.
- Every LLM call emits an audit record with redacted prompt/model/token usage.
- Transactional intents are verified against templates and local DB values before customer-facing output.
- Conversation logs store only redacted transcript text.

## End-to-end demo script

Run:

```bash
python scripts/e2e_demo.py
```

It demonstrates: ingest -> ASR -> NLU -> action -> retrieval -> summary, and prints redacted stored transcript.

## Contract publication note

`callsup-specs/intelligence_engine/openapi.yaml` and `callsup-specs/intelligence_engine/resources.json` are updated in this workspace. Open a PR from this branch to publish the contract.
