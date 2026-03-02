# callsup-knowledge-ops (consolidated starter)

This is a consolidated starter scaffold created during integration.

## Included artifacts
- `src/callsup_knowledge_ops/main.py`
- `openapi.yaml`
- `resources.json`
- `Dockerfile`

## Run
```bash
uvicorn src.callsup_knowledge_ops.main:app --host 0.0.0.0 --port 8000
```

## Notes
- Contract source of truth remains `callsup-specs`.
- Expand this starter with full ingest/query logic, tests, metrics, and redaction pipeline.
