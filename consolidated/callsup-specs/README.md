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

## Integration coordinator policy

This repo enforces integration governance through CI and PR templates:

1. **PR order is mandatory:** `callsup-specs` PR first, then module repo PR(s).
2. **Contract consistency is mandatory:** each module directory must keep `openapi.yaml` and `resources.json` aligned.
3. **Quality gates are mandatory:** lint/tests/docker build evidence must be included before merge.
4. **Mock-first is mandatory:** if dependencies are missing, proceed using mocks generated from available OpenAPI.
5. **Blockers must include mitigation:** every blocker requires a technical note and remaining deliverables must continue.

### Automation files

- `.github/workflows/contract-governance.yml`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `scripts/validate_contracts.py`
- `scripts/check_pr_governance.py`
- `templates/module-quality-gate.template.yml` (copy to each module repo as `.github/workflows/quality-gate.yml`)

Run locally:

```bash
python scripts/validate_contracts.py
```
