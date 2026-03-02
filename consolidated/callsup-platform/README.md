# CALLSUP Platform Module (v0.1.0)

Production-ready FastAPI service for CALLSUP Platform onboarding and resource manifest operations.

## Features
- FastAPI service version `v0.1.0`
- Endpoints: `/healthz`, `/readyz`, `/metrics`, `/platform/business` (POST/GET)
- SQLAlchemy persistence for onboarding records
- Structured JSON logging (`service`, `module`, `event`, `request_id`, `business_id`)
- Redaction policy before external processing
- Vault-only secret reference validation
- Encryption at rest for sensitive onboarding fields
- TLS-required runtime flag (`CALLSUP_PLATFORM_TLS_REQUIRED`)

## Naming and environment conventions
- Package/service: `svc-platform`
- Core env vars:
  - `CALLSUP_PLATFORM_ENV`
  - `CALLSUP_PLATFORM_DB_DSN`
  - `CALLSUP_PLATFORM_REDIS_URL`
  - `CALLSUP_PLATFORM_S3_BUCKET`
  - `CALLSUP_PLATFORM_VECTOR_NAMESPACE`
  - `CALLSUP_PLATFORM_VAULT_ENCRYPTION_KEY_REF` (must start with `vault://`)
  - `CALLSUP_PLATFORM_TLS_REQUIRED`

## Local runbook
1. Install:
   ```bash
   pip install -e .[test]
   ```
2. Run:
   ```bash
   uvicorn callsup_platform.main:app --reload
   ```
3. Verify:
   - `GET /healthz`
   - `GET /readyz`
   - `GET /metrics`

## Tests
```bash
pytest
```

Coverage policy is enforced at `>=70%` for `callsup_platform` core code.

## Docker
```bash
docker build -t callsup-platform:v0.1.0 .
docker run --rm -p 8000:8000 callsup-platform:v0.1.0
```

## Contract artifacts
- `callsup-specs/platform/openapi.yaml`
- `callsup-specs/platform/resources.json`
