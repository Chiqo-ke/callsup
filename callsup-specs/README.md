# callsup-specs (repo scaffold)

This scaffold contains minimal **OpenAPI 3.0** templates and shared schemas for the four core modules of CALLSUP: **Platform**, **Audio Engine**, **Intelligence Engine**, and **Knowledge & Ops**. Use these templates as the canonical `openapi.yaml` files for each service and update them via PRs to this repo.

> Note: The canonical contract file is `openapi.yaml` (not `openai.yaml`). Each service places `openapi.yaml` at the repo root and publishes a `resources.json` manifest describing service metadata.

## Included files

- `README.md`
- `schemas/common.json`
- `platform/openapi.yaml`
- `audio_engine/openapi.yaml`
- `intelligence_engine/openapi.yaml`
- `knowledge_ops/openapi.yaml`
- `resources.example.json`

## Usage

1. Copy each `openapi.yaml` into the corresponding module repo under the service root. Example: `callsup-platform/openapi.yaml`.
2. Each service MUST commit its `openapi.yaml` and a `resources.json` manifest to this `callsup-specs` repo and open a PR.
3. If a consuming service needs a mock of a provider, generate a mock server from that provider's `openapi.yaml`.
4. Follow the CALLSUP System Contract for naming, PII redaction, and event schemas.

## Next steps & suggested workflow

1. Share this repo URL with all agent workers.
2. Require workers to publish `resources.json` and open PRs before integration tests run.
3. Treat `callsup-specs` as canonical for inter-module API contracts.
