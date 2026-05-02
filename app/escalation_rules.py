"""
Escalation rules storage for CALLSUP.

Rules for a business are persisted as a JSON array at:
  data/escalations/{business_id}/rules.json

Each rule has a human-authored rule_text and an optional AI-refined version.
The AI-refined text is what gets injected into the LLM system prompt.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import urllib.request

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel

from app.auth import UserRecord, get_current_user
from app.config import get_settings
from app.models import EscalationRule

logger = logging.getLogger("callsup.escalation_rules")

router = APIRouter(prefix="/escalation-rules", tags=["escalation-rules"])

# ── Schemas ───────────────────────────────────────────────────────────────────

class CreateRuleRequest(BaseModel):
    rule_text: str
    priority: str = "medium"
    refine_with_ai: bool = False


class UpdateRuleRequest(BaseModel):
    rule_text: str | None = None
    ai_refined_text: str | None = None
    priority: str | None = None
    is_active: bool | None = None
    refine_with_ai: bool = False


# ── Storage helpers ───────────────────────────────────────────────────────────

def _esc_dir(business_id: str) -> Path:
    settings = get_settings()
    p = Path(settings.data_dir) / "escalations" / business_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def _rules_path(business_id: str) -> Path:
    return _esc_dir(business_id) / "rules.json"


def _load_rules(business_id: str) -> list[EscalationRule]:
    p = _rules_path(business_id)
    if not p.exists():
        return []
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        return [EscalationRule(**item) for item in raw]
    except Exception:
        return []


def _save_rules(business_id: str, rules: list[EscalationRule]) -> None:
    _rules_path(business_id).write_text(
        json.dumps([r.model_dump() for r in rules], indent=2),
        encoding="utf-8",
    )


def list_rules(business_id: str) -> list[EscalationRule]:
    """Return all escalation rules for a business (used internally)."""
    return _load_rules(business_id)


def list_active_rules(business_id: str) -> list[EscalationRule]:
    """Return only active rules (used when building LLM system prompt)."""
    return [r for r in _load_rules(business_id) if r.is_active]


# ── LLM rule refinement ───────────────────────────────────────────────────────

def _refine_rule_with_llm(rule_text: str) -> str:
    settings = get_settings()
    prompt = (
        "You are configuring an AI call-centre assistant. "
        "Below is a raw escalation rule written by a business operator. "
        "Rewrite it as a clear, unambiguous single sentence that an LLM can reliably apply. "
        "Keep the intent and specifics exactly the same. Return only the refined rule, no preamble.\n\n"
        f"Raw rule: {rule_text}"
    )
    payload = json.dumps({"prompt": prompt, "model": "gpt-4o"}).encode("utf-8")
    req = urllib.request.Request(
        f"{settings.llm_adapter_url}/v1/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data.get("text", rule_text).strip()
    except Exception as exc:
        logger.warning("rule_refinement_failed: %s", exc)
        return rule_text


# ── Routes ────────────────────────────────────────────────────────────────────

CurrentUser = Annotated[UserRecord, Depends(get_current_user)]


@router.get("", response_model=list[EscalationRule])
def get_rules(current_user: CurrentUser) -> list[EscalationRule]:
    return list_rules(current_user.business_id)


@router.post("", response_model=EscalationRule, status_code=201)
def create_rule(body: CreateRuleRequest, current_user: CurrentUser) -> EscalationRule:
    if body.priority not in ("high", "medium", "low"):
        raise HTTPException(status_code=422, detail="priority must be high, medium, or low")
    now = datetime.now(timezone.utc).isoformat()
    ai_refined = None
    if body.refine_with_ai:
        ai_refined = _refine_rule_with_llm(body.rule_text)
    rule = EscalationRule(
        id=str(uuid.uuid4()),
        business_id=current_user.business_id,
        rule_text=body.rule_text,
        ai_refined_text=ai_refined,
        priority=body.priority,  # type: ignore[arg-type]
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    rules = _load_rules(current_user.business_id)
    rules.append(rule)
    _save_rules(current_user.business_id, rules)
    logger.info("escalation_rule_created business_id=%s id=%s", current_user.business_id, rule.id)
    return rule


@router.put("/{rule_id}", response_model=EscalationRule)
def update_rule(
    rule_id: str,
    body: UpdateRuleRequest,
    current_user: CurrentUser,
) -> EscalationRule:
    rules = _load_rules(current_user.business_id)
    rule = next((r for r in rules if r.id == rule_id), None)
    if rule is None:
        raise HTTPException(status_code=404, detail="Escalation rule not found")
    if body.rule_text is not None:
        rule.rule_text = body.rule_text
    if body.ai_refined_text is not None:
        rule.ai_refined_text = body.ai_refined_text
    if body.priority is not None:
        if body.priority not in ("high", "medium", "low"):
            raise HTTPException(status_code=422, detail="priority must be high, medium, or low")
        rule.priority = body.priority  # type: ignore[assignment]
    if body.is_active is not None:
        rule.is_active = body.is_active
    if body.refine_with_ai:
        rule.ai_refined_text = _refine_rule_with_llm(rule.rule_text)
    rule.updated_at = datetime.now(timezone.utc).isoformat()
    _save_rules(current_user.business_id, rules)
    logger.info("escalation_rule_updated business_id=%s id=%s", current_user.business_id, rule_id)
    return rule


@router.delete("/{rule_id}", status_code=204, response_model=None)
def delete_rule(rule_id: str, current_user: CurrentUser) -> None:
    rules = _load_rules(current_user.business_id)
    if not any(r.id == rule_id for r in rules):
        raise HTTPException(status_code=404, detail="Escalation rule not found")
    _save_rules(current_user.business_id, [r for r in rules if r.id != rule_id])
    logger.info("escalation_rule_deleted business_id=%s id=%s", current_user.business_id, rule_id)
