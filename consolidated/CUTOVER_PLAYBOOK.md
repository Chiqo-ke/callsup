# CALLSUP Cutover Playbook

Date: 2026-03-01

This playbook is the execution-ready plan to move consolidated artifacts into their target repositories with enforced PR ordering and clean merge gates.

## 1) Repository targets and exact branch names

Create branches from each repo `main`:

- `callsup-specs`: `cutover/specs-2026-03-01-baseline`
- `callsup-platform`: `cutover/platform-2026-03-01-baseline`
- `callsup-audio-engine`: `cutover/audio-engine-2026-03-01-baseline`
- `callsup-intelligence-engine`: `cutover/intelligence-engine-2026-03-01-baseline`
- `callsup-knowledge-ops`: `cutover/knowledge-ops-2026-03-01-baseline`
- Integration repo (or orchestrator repo): `cutover/integration-2026-03-01-baseline`

## 2) Mandatory PR merge order

1. `callsup-specs` PR (contracts and governance)
2. `callsup-platform` PR
3. `callsup-audio-engine` PR
4. `callsup-intelligence-engine` PR
5. `callsup-knowledge-ops` PR
6. Integration PR (cross-module mocked integration + release notes)

No module PR merges before step 1 is approved/merged.

## 3) First PR content per repo

### A) callsup-specs (PR-01)
Source: `callsup/consolidated/callsup-specs`

Include:
- All module contracts under `platform/`, `audio_engine/`, `intelligence_engine/`, `knowledge_ops/`
- All module `resources.json`
- Shared schema `schemas/common.json`
- Governance assets:
  - `.github/workflows/contract-governance.yml`
  - `.github/PULL_REQUEST_TEMPLATE.md`
  - `scripts/validate_contracts.py`
  - `scripts/check_pr_governance.py`
  - `templates/module-quality-gate.template.yml`
  - `docs/BLOCKER_TECHNICAL_NOTE_TEMPLATE.md`

PR title:
- `feat(specs): baseline contracts + governance gates v0.1.0`

### B) callsup-platform (PR-02)
Source: `callsup/consolidated/callsup-platform`

Include:
- Service code (`callsup_platform/`)
- `Dockerfile`, `README.md`, test suite, packaging files
- Add `.github/workflows/quality-gate.yml` from specs template
- Ensure root `openapi.yaml` + `resources.json` match `callsup-specs/platform/*` before merge

PR title:
- `feat(platform): baseline module implementation aligned to callsup-specs`

### C) callsup-audio-engine (PR-03)
Source: `callsup/consolidated/callsup-audio-engine`

Include:
- Service code (`app/`), tests, Docker and requirements
- Root `openapi.yaml` and `resources.json`
- `.github/workflows/quality-gate.yml`
- Confirm transcript schema compatibility with `schemas/common.json`

PR title:
- `feat(audio-engine): baseline module implementation with schema-aligned transcript API`

### D) callsup-intelligence-engine (PR-04)
Source: `callsup/consolidated/callsup-intelligence-engine`

Include:
- Service code (`src/`, `scripts/`), tests, Docker and project config
- Root `openapi.yaml` and `resources.json`
- `.github/workflows/quality-gate.yml`
- Keep adapter-only LLM interface and redacted audit behavior in follow-up checks

PR title:
- `feat(intelligence-engine): baseline module implementation aligned to specs`

### E) callsup-knowledge-ops (PR-05)
Source: `callsup/consolidated/callsup-knowledge-ops`

Include:
- Starter service scaffold (`src/callsup_knowledge_ops/`)
- Root `openapi.yaml`, `resources.json`, `Dockerfile`, `README.md`
- `.github/workflows/quality-gate.yml`

PR title:
- `feat(knowledge-ops): starter baseline scaffold aligned to specs`

### F) integration (PR-06)
Source: integration repo

Include:
- Mock-first orchestration tests across all modules
- End-to-end smoke workflow using approved specs contracts
- Coordinator release note referencing PR-01..PR-05 SHAs

PR title:
- `chore(integration): baseline cross-module mocked integration`

## 4) Commit-ready change groups (copy as-is)

Use these groups to keep commits small and reviewable.

### Group S1 (spec contracts)
- `platform/openapi.yaml`
- `platform/resources.json`
- `audio_engine/openapi.yaml`
- `audio_engine/resources.json`
- `intelligence_engine/openapi.yaml`
- `intelligence_engine/resources.json`
- `knowledge_ops/openapi.yaml`
- `knowledge_ops/resources.json`
- `schemas/common.json`
- `resources.example.json`

Commit message:
- `feat(specs): add baseline OpenAPI + resources manifests`

### Group S2 (spec governance)
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/workflows/contract-governance.yml`
- `scripts/validate_contracts.py`
- `scripts/check_pr_governance.py`
- `templates/module-quality-gate.template.yml`
- `docs/BLOCKER_TECHNICAL_NOTE_TEMPLATE.md`
- `README.md`

Commit message:
- `chore(specs): add PR governance and contract validation automation`

### Group P1 (platform baseline)
- `callsup_platform/**`
- `tests/**`
- `Dockerfile`
- `README.md`
- `pyproject.toml`
- `.github/workflows/quality-gate.yml`

Commit message:
- `feat(platform): import consolidated baseline implementation`

### Group A1 (audio baseline)
- `app/**`
- `tests/**`
- `Dockerfile`
- `README.md`
- `requirements*.txt`
- `pytest.ini`
- `openapi.yaml`
- `resources.json`
- `.github/workflows/quality-gate.yml`

Commit message:
- `feat(audio-engine): import consolidated baseline implementation`

### Group I1 (intelligence baseline)
- `src/**`
- `scripts/**`
- `Dockerfile`
- `README.md`
- `pyproject.toml`
- `openapi.yaml`
- `resources.json`
- `.github/workflows/quality-gate.yml`

Commit message:
- `feat(intelligence-engine): import consolidated baseline implementation`

### Group K1 (knowledge starter)
- `src/callsup_knowledge_ops/**`
- `openapi.yaml`
- `resources.json`
- `Dockerfile`
- `README.md`
- `.github/workflows/quality-gate.yml`

Commit message:
- `feat(knowledge-ops): import consolidated starter scaffold`

## 5) PR body minimum checklist (required)

Every PR must include:
- Specs PR URL
- Module PR URL(s)
- Mock-first status
- Blockers & mitigation
- PR Order Confirmation

Use `callsup-specs/.github/PULL_REQUEST_TEMPLATE.md` as source.

## 6) Coordinator runbook (execution)

1. Merge PR-01.
2. Rebase PR-02..PR-05 on latest main.
3. Ensure each module CI gate passes (lint, tests, docker build).
4. If dependency missing: use mocks and attach blocker note.
5. Merge PR-06 integration and publish release notes.
