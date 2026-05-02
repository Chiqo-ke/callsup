"""
Escalation queue storage for CALLSUP.

Tickets for a business are persisted at:
  data/escalations/{business_id}/queue.json

Human agents poll GET /escalation-queue to see pending tickets, then claim
and resolve them.  The voice-chat endpoint calls create_ticket_internal()
directly (no HTTP round-trip needed).
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.auth import UserRecord, get_current_user
from app.config import get_settings
from app.models import EscalationTicket

logger = logging.getLogger("callsup.escalation_queue")

router = APIRouter(prefix="/escalation-queue", tags=["escalation-queue"])

# ── SSE event bus ──────────────────────────────────────────────────────────────
_sse_subscribers: list[asyncio.Queue] = []


async def broadcast_ticket(ticket_dict: dict) -> None:
    """Push a new ticket to all connected SSE subscribers."""
    for q in list(_sse_subscribers):
        try:
            q.put_nowait(ticket_dict)
        except asyncio.QueueFull:
            pass

# ── Schemas ───────────────────────────────────────────────────────────────────

class CreateTicketRequest(BaseModel):
    session_id: str
    reason: str
    priority: str = "medium"
    rule_triggered: str | None = None
    conv_id: str | None = None
    summary: str | None = None


class UpdateTicketRequest(BaseModel):
    status: str
    claimed_by: str | None = None


# ── Storage helpers ───────────────────────────────────────────────────────────

def _esc_dir(business_id: str) -> Path:
    settings = get_settings()
    p = Path(settings.data_dir) / "escalations" / business_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def _queue_path(business_id: str) -> Path:
    return _esc_dir(business_id) / "queue.json"


def _load_queue(business_id: str) -> list[EscalationTicket]:
    p = _queue_path(business_id)
    if not p.exists():
        return []
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        return [EscalationTicket(**item) for item in raw]
    except Exception:
        return []


def _save_queue(business_id: str, tickets: list[EscalationTicket]) -> None:
    _queue_path(business_id).write_text(
        json.dumps([t.model_dump() for t in tickets], indent=2),
        encoding="utf-8",
    )


# ── Internal callable (used by voice-chat endpoint) ──────────────────────────

def create_ticket_internal(
    *,
    business_id: str,
    session_id: str,
    reason: str,
    priority: str = "medium",
    rule_triggered: str | None = None,
    conv_id: str | None = None,
    summary: str | None = None,
    conversation_history: list[dict] | None = None,
) -> EscalationTicket:
    now = datetime.now(timezone.utc).isoformat()
    ticket = EscalationTicket(
        id=str(uuid.uuid4()),
        business_id=business_id,
        conv_id=conv_id,
        session_id=session_id,
        reason=reason,
        priority=priority,  # type: ignore[arg-type]
        summary=summary,
        rule_triggered=rule_triggered,
        status="pending",
        created_at=now,
        claimed_by=None,
        resolved_at=None,
        conversation_history=conversation_history or [],
    )
    tickets = _load_queue(business_id)
    tickets.append(ticket)
    _save_queue(business_id, tickets)
    logger.info(
        "escalation_ticket_created business_id=%s id=%s reason=%s",
        business_id,
        ticket.id,
        reason,
    )
    return ticket


# ── Routes ────────────────────────────────────────────────────────────────────

CurrentUser = Annotated[UserRecord, Depends(get_current_user)]


@router.get("/stream")
async def stream_escalations(token: str = Query(...)) -> StreamingResponse:
    """SSE endpoint — push new tickets to connected dashboard clients instantly."""
    from app.auth import _decode_token  # noqa: PLC2701
    try:
        _decode_token(token)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Invalid token")

    queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    _sse_subscribers.append(queue)

    async def event_generator():
        try:
            yield "data: connected\n\n"
            while True:
                try:
                    ticket_dict = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(ticket_dict)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            if queue in _sse_subscribers:
                _sse_subscribers.remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{ticket_id}", response_model=EscalationTicket)
def get_ticket(ticket_id: str, current_user: CurrentUser) -> EscalationTicket:
    tickets = _load_queue(current_user.business_id)
    ticket = next((t for t in tickets if t.id == ticket_id), None)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.get("", response_model=list[EscalationTicket])
def get_queue(current_user: CurrentUser, status: str | None = None) -> list[EscalationTicket]:
    tickets = _load_queue(current_user.business_id)
    if status:
        tickets = [t for t in tickets if t.status == status]
    # Newest first
    tickets.sort(key=lambda t: t.created_at, reverse=True)
    return tickets


@router.post("", response_model=EscalationTicket, status_code=201)
def create_ticket(body: CreateTicketRequest, current_user: CurrentUser) -> EscalationTicket:
    if body.priority not in ("high", "medium", "low"):
        raise HTTPException(status_code=422, detail="priority must be high, medium, or low")
    return create_ticket_internal(
        business_id=current_user.business_id,
        session_id=body.session_id,
        reason=body.reason,
        priority=body.priority,
        rule_triggered=body.rule_triggered,
        conv_id=body.conv_id,
        summary=body.summary,
    )


@router.put("/{ticket_id}", response_model=EscalationTicket)
def update_ticket(
    ticket_id: str,
    body: UpdateTicketRequest,
    current_user: CurrentUser,
) -> EscalationTicket:
    if body.status not in ("pending", "claimed", "resolved"):
        raise HTTPException(
            status_code=422, detail="status must be pending, claimed, or resolved"
        )
    tickets = _load_queue(current_user.business_id)
    ticket = next((t for t in tickets if t.id == ticket_id), None)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.status = body.status  # type: ignore[assignment]
    if body.claimed_by is not None:
        ticket.claimed_by = body.claimed_by
    if body.status == "resolved":
        ticket.resolved_at = datetime.now(timezone.utc).isoformat()
    _save_queue(current_user.business_id, tickets)
    logger.info(
        "escalation_ticket_updated business_id=%s id=%s status=%s",
        current_user.business_id,
        ticket_id,
        body.status,
    )
    return ticket
