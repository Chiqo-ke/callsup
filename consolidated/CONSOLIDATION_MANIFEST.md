# CALLSUP Consolidation Manifest

Date: 2026-03-01

## Canonical source mapping

- `callsup-platform` <- `callsup.worktrees/copilot-worktree-2026-03-01T20-06-59`
- `callsup-audio-engine` <- `callsup.worktrees/copilot-worktree-2026-03-01T20-08-58`
- `callsup-intelligence-engine` <- `callsup.worktrees/copilot-worktree-2026-03-01T20-12-23`
- `callsup-knowledge-ops` <- consolidated starter scaffold (generated)
- `callsup-specs` <- `callsup/callsup-specs` (includes governance scripts + workflows)

## Normalization applied

- Removed nested `.git` folders from copied module folders.
- Removed duplicate nested `callsup-specs` folders from module folders.
- Added starter structure for `callsup-knowledge-ops` with `openapi.yaml`, `resources.json`, `Dockerfile`, and FastAPI health/readiness app.

## Required PR order (enforced)

1. `callsup-specs` PR first (contracts + resources + governance scripts).
2. Module PRs (`callsup-platform`, `callsup-audio-engine`, `callsup-intelligence-engine`, `callsup-knowledge-ops`).
3. Integration PR (cross-module mocked integration and release notes).

## Immediate module actions

### callsup-platform
- Align package layout to `/src/callsup_platform` if not already complete.
- Ensure `openapi.yaml` and `resources.json` match `callsup-specs/platform/*`.
- Enable module CI gate from `callsup-specs/templates/module-quality-gate.template.yml`.

### callsup-audio-engine
- Keep transcript schema compatibility with `schemas/common.json`.
- Confirm PII redaction before third-party transfer and keep tests green.
- Enable module CI gate template and run lint/tests/docker build.

### callsup-intelligence-engine
- Keep LLM access only through local adapter contract and audit logs redacted.
- Keep `openapi.yaml` and `resources.json` aligned with `callsup-specs/intelligence_engine/*`.
- Enable module CI gate template and run lint/tests/docker build.

### callsup-knowledge-ops
- Expand starter scaffold to full ingest/query implementation.
- Add tests, metrics endpoint, redaction path checks, and README runbook.
- Enable module CI gate template and run lint/tests/docker build.

## Blocker policy

When blocked by missing dependencies, proceed with mock-first integration and attach technical note using:

- `callsup-specs/docs/BLOCKER_TECHNICAL_NOTE_TEMPLATE.md`

## Coordinator validation commands

```powershell
Set-Location c:/Users/nyaga/Documents/callsup/consolidated/callsup-specs
..\..\..\.venv\Scripts\python.exe scripts/validate_contracts.py
```
