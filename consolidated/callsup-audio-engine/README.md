# CALLSUP Audio Engine Service (v0.1.0)

FastAPI service for audio ingest and transcript retrieval with strict `TranscriptSegment` compatibility.

## Endpoints

- `POST /audio/ingest` (multipart: `business_id`, `conv_id`, `file`) -> `202 accepted`
- `GET /audio/transcript/{conv_id}` -> transcript segments
- `GET /health` -> service health
- `GET /metrics` -> Prometheus metrics

## Quickstart

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

## Example payloads

### Ingest audio

```bash
curl -X POST "http://localhost:8000/audio/ingest" ^
  -F "business_id=biz-123" ^
  -F "conv_id=conv-abc" ^
  -F "file=@sample.wav"
```

### Retrieve transcript

```bash
curl "http://localhost:8000/audio/transcript/conv-abc"
```

Example response:

```json
[
  {
    "business_id": "biz-123",
    "conv_id": "conv-abc",
    "segment_id": "4f8f7f7f-bf7f-4f8f-9f7f-7f7f7f7f7f7f",
    "speaker": "customer",
    "start_ts": "2026-03-01T20:00:00Z",
    "end_ts": "2026-03-01T20:00:04Z",
    "text": "Customer shared [REDACTED_PHONE] and [REDACTED_EMAIL] for follow up",
    "confidence": 0.95
  }
]
```

## Security and compliance

- **PII redaction:** canonical redaction (`email`, `phone`, `ssn`, `card`) applied before mock third-party transcription calls.
- **Vault key refs:** configure refs via env:
  - `CALLSUP_AUDIO_ENGINE_VAULT_API_KEY_REF`
  - `CALLSUP_AUDIO_ENGINE_VAULT_ENCRYPTION_KEY_REF`
- **Encryption at rest:** uploaded audio bytes are encrypted with Fernet before writing to disk (`data/audio/*.bin`).
- **TLS in transit:** set `CALLSUP_AUDIO_ENGINE_ENFORCE_TLS_IN_TRANSIT=true` and `CALLSUP_AUDIO_ENGINE_ALLOW_INSECURE_HTTP=false`.

## Tests

```bash
pytest
```

Pytest is configured to fail below 70% coverage for `app/`.
