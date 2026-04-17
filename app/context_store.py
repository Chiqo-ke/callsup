"""
Business context storage for CALLSUP.

Each context item is stored as a Markdown file:
  data/contexts/{business_id}/{item_id}.md

A companion JSON index is maintained at:
  data/contexts/{business_id}/index.json

The index holds metadata (id, label, type, created_at, updated_at).
The .md file holds the content body.

Optional LLM rewrite: sends the raw content to the LLM adapter
(POST /v1/generate) and stores the improved version.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import urllib.request
import urllib.error

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import UserRecord, get_current_user
from app.config import get_settings

logger = logging.getLogger("callsup.context")

router = APIRouter(prefix="/context", tags=["context"])

# ── Schemas ───────────────────────────────────────────────────────────────────

class ContextItemMeta(BaseModel):
    id: str
    label: str
    type: str  # "manual" | "file"
    file_name: str | None = None
    created_at: str
    updated_at: str


class ContextItem(ContextItemMeta):
    content: str


class CreateContextRequest(BaseModel):
    label: str
    content: str
    type: str = "manual"
    file_name: str | None = None
    refine_with_ai: bool = False


class UpdateContextRequest(BaseModel):
    label: str | None = None
    content: str | None = None
    refine_with_ai: bool = False


# ── Storage helpers ───────────────────────────────────────────────────────────

def _ctx_dir(business_id: str) -> Path:
    settings = get_settings()
    p = Path(settings.data_dir) / "contexts" / business_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def _index_path(business_id: str) -> Path:
    return _ctx_dir(business_id) / "index.json"


def _load_index(business_id: str) -> list[ContextItemMeta]:
    p = _index_path(business_id)
    if not p.exists():
        return []
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        return [ContextItemMeta(**item) for item in raw]
    except Exception:
        return []


def _save_index(business_id: str, items: list[ContextItemMeta]) -> None:
    _index_path(business_id).write_text(
        json.dumps([i.model_dump() for i in items], indent=2),
        encoding="utf-8",
    )


def _read_content(business_id: str, item_id: str) -> str:
    md_path = _ctx_dir(business_id) / f"{item_id}.md"
    if not md_path.exists():
        return ""
    return md_path.read_text(encoding="utf-8")


def _write_content(business_id: str, item_id: str, content: str) -> None:
    (_ctx_dir(business_id) / f"{item_id}.md").write_text(content, encoding="utf-8")


def _delete_content(business_id: str, item_id: str) -> None:
    md_path = _ctx_dir(business_id) / f"{item_id}.md"
    if md_path.exists():
        md_path.unlink()


# ── LLM rewrite ───────────────────────────────────────────────────────────────

def _rewrite_with_llm(label: str, raw_content: str) -> str:
    settings = get_settings()
    prompt = (
        f"You are helping a business configure their AI call assistant. "
        f"Rewrite the following business context entry titled '{label}' as a clear, "
        f"well-structured Markdown document. Keep all factual details, improve clarity and "
        f"formatting. Do not add information that is not present. Return only the Markdown.\n\n"
        f"{raw_content}"
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
            return data.get("text", raw_content)
    except Exception as exc:
        logger.warning("LLM rewrite failed, storing original: %s", exc)
        return raw_content


# ── Routes ────────────────────────────────────────────────────────────────────

CurrentUser = Annotated[UserRecord, Depends(get_current_user)]


@router.get("", response_model=list[ContextItem])
def list_context(current_user: CurrentUser) -> list[ContextItem]:
    meta_items = _load_index(current_user.business_id)
    result = []
    for meta in meta_items:
        content = _read_content(current_user.business_id, meta.id)
        result.append(ContextItem(**meta.model_dump(), content=content))
    return result


@router.post("", response_model=ContextItem, status_code=201)
def create_context(body: CreateContextRequest, current_user: CurrentUser) -> ContextItem:
    item_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    content = body.content
    if body.refine_with_ai:
        content = _rewrite_with_llm(body.label, content)
    _write_content(current_user.business_id, item_id, content)
    meta = ContextItemMeta(
        id=item_id,
        label=body.label,
        type=body.type,
        file_name=body.file_name,
        created_at=now,
        updated_at=now,
    )
    index = _load_index(current_user.business_id)
    index.append(meta)
    _save_index(current_user.business_id, index)
    logger.info("context_created business_id=%s id=%s", current_user.business_id, item_id)
    return ContextItem(**meta.model_dump(), content=content)


@router.put("/{item_id}", response_model=ContextItem)
def update_context(
    item_id: str,
    body: UpdateContextRequest,
    current_user: CurrentUser,
) -> ContextItem:
    index = _load_index(current_user.business_id)
    meta = next((i for i in index if i.id == item_id), None)
    if meta is None:
        raise HTTPException(status_code=404, detail="Context item not found")
    if body.label is not None:
        meta.label = body.label
    content = _read_content(current_user.business_id, item_id)
    if body.content is not None:
        content = body.content
    if body.refine_with_ai:
        content = _rewrite_with_llm(meta.label, content)
    meta.updated_at = datetime.now(timezone.utc).isoformat()
    _write_content(current_user.business_id, item_id, content)
    _save_index(current_user.business_id, index)
    return ContextItem(**meta.model_dump(), content=content)


@router.delete("/{item_id}", status_code=204, response_model=None)
def delete_context(item_id: str, current_user: CurrentUser) -> None:
    index = _load_index(current_user.business_id)
    if not any(i.id == item_id for i in index):
        raise HTTPException(status_code=404, detail="Context item not found")
    new_index = [i for i in index if i.id != item_id]
    _save_index(current_user.business_id, new_index)
    _delete_content(current_user.business_id, item_id)
    logger.info("context_deleted business_id=%s id=%s", current_user.business_id, item_id)
