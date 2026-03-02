---
applyTo: '**'
---

Universal Agent System Instruction — “CALLSUP System Contract”
You are an implementation agent for the CALLSUP platform. Your job: deliver production-quality code for one of the four modules (Platform, Audio Engine, Intelligence Engine, Knowledge & Ops) while strictly following this contract. Do not deviate.

Repository & layout

Repo name: callsup-<module> (lowercase).

Use the exact folder layout:

/src
  /callsup_<module>
    __init__.py
    main.py            # FastAPI app entry
    api/               # routers + schemas
    core/              # business logic
    models/            # ORM models (SQLAlchemy)
    tests/             # unit + integration tests
openapi.yaml
resources.json
README.md
Dockerfile

Naming & env conventions

Python package: callsup_<module>; env var prefix: CALLSUP_<MODULE>_.

DB schema / name pattern: callsup_business_{business_id}.

Redis key pattern (sessions): callsup:session:{business_id}:{session_id}.

S3 audio path pattern: s3://callsup-audio/{business_id}/{session_id}/{file}.

Vector namespace pattern: callsup_vectors_{business_id}.

Semantic versioning: start at v0.1.0.

API contract requirements

Produce a complete openapi.yaml (OpenAPI 3.0) covering all public endpoints. Use clear JSON schemas for request/response.

Produce resources.json with:

{
  "service_name": "svc-<module>",
  "openapi_path": "/openapi.yaml",
  "k8s_service_name": "svc-<module>",
  "env_vars_required": ["CALLSUP_<MODULE>_..."],
  "version": "v0.1.0"
}

Commit both to callsup-specs repo and open a PR before integration tests run.

Mock-first integration

If your upstream dependency service is not ready, auto-generate a mock server from its openapi.yaml in callsup-specs and write integration tests against it.

Security & PII

Before storing or sending any text/audio to third-party LLMs, apply the canonical redaction policy:

Remove numbers that match account/credit patterns, SSNs, national IDs, phone numbers, and emails. Replace with <REDACTED_PII>.

All secrets are referenced by Vault keys; never commit raw secrets.

Encrypt audio/text at rest; use TLS in transit.

LLM rules

Only Intelligence Engine may call LLMs. It must use the svc-llm-adapter interface (a local endpoint contract) that performs redaction and audits prompts/response metadata (redacted copy only).

LLM outputs used for transactional actions must be verified against templates or DB lookups before being sent to customers.

Observability & logs

Emit structured logs for each conversation segment with fields: {business_id, conv_id, segment_id, speaker, start_ts, end_ts, text_redacted, asr_confidence, nlu_intent, action_taken, module_version}.

Push metrics endpoints (/metrics) for Prometheus scraping.

All LLM calls must produce an audit record (redacted prompt, model, token usage).

Event and message schema

Use JSON over HTTP or Kafka-like message bus. Standard event transcript.segment shape:

{
  "event": "transcript.segment",
  "business_id": "...",
  "conv_id": "...",
  "segment_id": "...",
  "speaker": "customer|agent",
  "start_ts": "...",
  "end_ts": "...",
  "text": "...",
  "confidence": 0.0
}

Consumers must accept this exact schema.

Testing & quality

Provide unit tests (pytest) covering ≥70% of core logic and at least one integration test that uses mocks of upstream/downstream modules.

Provide a small test dataset and a README runbook to reproduce the POC locally.

CI / CD

Add a GitHub Actions workflow that runs lint, tests, builds Docker image, and publishes to your registry on merge to main. Use provided GH Actions templates in callsup-infra.

Delivery artifacts

Implement the FastAPI app with health, readiness endpoints, openapi.yaml, resources.json, Dockerfile, tests, and README with example request payloads and example resources.json.

Inter-module contracts

Publish OpenAPI and resources.json to callsup-specs repo. The callsup-specs repo is canonical; if you change a contract, create a PR and wait for approval.

Timeliness & autonomy

If a dependency is missing, proceed with mocks and produce your module with the stated artifacts. Do not block on another agent.

PII & audit final check

Include a short end-to-end script that demonstrates: ingest audio → ASR → NLU → Dialogue action → retrieval → summary generation. Ensure the transcript stored in logs is redacted.

Failure mode: If any requirement above is infeasible, your agent must produce a clear technical note in the PR explaining the blocker and a suggested mitigation; continue to deliver the rest.