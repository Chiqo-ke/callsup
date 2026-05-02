"""
Utility helpers for resolving business name and loading business context
markdown files into a single string for system prompt injection.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
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

    Temporary alerts whose ``expires_at`` timestamp is in the past are silently
    skipped — they will not appear in the returned string.

    Active alerts are placed under a prominent ``## ACTIVE ALERTS`` heading so
    the LLM treats them with appropriate urgency.  Regular context items follow
    under ``## BUSINESS INFORMATION``.

    Returns an empty string when no non-expired context items exist.
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

    now = datetime.now(timezone.utc)

    alert_parts: list[str] = []
    context_parts: list[str] = []

    for item in index:
        item_id = item.get("id", "")
        label = item.get("label", item_id)
        expires_at_raw: str | None = item.get("expires_at")

        # Skip expired items
        if expires_at_raw:
            try:
                expires_dt = datetime.fromisoformat(expires_at_raw)
                # Ensure timezone-aware comparison
                if expires_dt.tzinfo is None:
                    expires_dt = expires_dt.replace(tzinfo=timezone.utc)
                if expires_dt <= now:
                    logger.debug(
                        "load_business_context skipping expired item id=%s label=%s",
                        item_id, label,
                    )
                    continue
            except Exception as exc:
                logger.warning(
                    "load_business_context bad expires_at id=%s: %s", item_id, exc
                )

        md_path = ctx_dir / f"{item_id}.md"
        if not md_path.exists():
            continue
        try:
            content = md_path.read_text(encoding="utf-8").strip()
        except Exception as exc:
            logger.warning("load_business_context item read failed id=%s: %s", item_id, exc)
            continue
        if not content:
            continue

        is_alert = item.get("is_alert", False)
        if is_alert:
            # Include expiry hint in the alert text for the LLM
            expiry_note = ""
            if expires_at_raw:
                try:
                    expiry_dt = datetime.fromisoformat(expires_at_raw)
                    if expiry_dt.tzinfo is None:
                        expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
                    expiry_note = f" *(expires {expiry_dt.strftime('%Y-%m-%d %H:%M UTC')})*"
                except Exception:
                    pass
            alert_parts.append(f"### {label}{expiry_note}\n{content}")
        else:
            context_parts.append(f"## {label}\n{content}")

    sections: list[str] = []
    if alert_parts:
        sections.append(
            "## ACTIVE ALERTS\n"
            "The following temporary notices are currently active. "
            "Proactively inform callers if their query is related to any of these.\n\n"
            + "\n\n".join(alert_parts)
        )
    if context_parts:
        sections.append("\n\n".join(context_parts))

    return "\n\n".join(sections)
