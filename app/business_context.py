"""
Utility helpers for resolving business name and loading business context
markdown files into a single string for system prompt injection.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger("callsup.business_context")


def get_business_name(business_id: str, data_dir: str = "data") -> str:
    """Return the business_name for a given business_id.

    Falls back to username if business_name is not set, and to the raw
    business_id UUID if the user record cannot be found at all.
    """
    users_path = Path(data_dir) / "users.json"
    try:
        if users_path.exists():
            records = json.loads(users_path.read_text(encoding="utf-8"))
            for user in records:
                if user.get("business_id") == business_id:
                    name = user.get("business_name", "").strip()
                    if name:
                        return name
                    # fall back to username if business_name absent/empty
                    return user.get("username", business_id)
    except Exception as exc:
        logger.warning("get_business_name failed: %s", exc)
    return business_id


def load_business_context(business_id: str, data_dir: str = "data") -> str:
    """Read all context markdown files for a business and return them as a
    single formatted string suitable for inclusion in a system prompt.

    Returns an empty string when no context items exist.
    """
    ctx_dir = Path(data_dir) / "contexts" / business_id
    index_path = ctx_dir / "index.json"

    if not index_path.exists():
        return ""

    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("load_business_context index read failed: %s", exc)
        return ""

    parts: list[str] = []
    for item in index:
        item_id = item.get("id", "")
        label = item.get("label", item_id)
        md_path = ctx_dir / f"{item_id}.md"
        if not md_path.exists():
            continue
        try:
            content = md_path.read_text(encoding="utf-8").strip()
        except Exception as exc:
            logger.warning("load_business_context item read failed id=%s: %s", item_id, exc)
            continue
        if content:
            parts.append(f"## {label}\n{content}")

    return "\n\n".join(parts)
