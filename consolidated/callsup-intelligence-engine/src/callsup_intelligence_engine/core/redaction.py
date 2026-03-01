from __future__ import annotations

import re

PII_PATTERNS = (
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # SSN-like
    re.compile(r"\b(?:\+?\d{1,2}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?){2}\d{4}\b"),  # Phone
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),  # Email
    re.compile(r"\b(?:\d[ -]*?){13,19}\b"),  # Card/account-like
)

REDACTION_TOKEN = "<REDACTED_PII>"


def redact_pii(text: str) -> tuple[str, int]:
    redacted = text
    redaction_count = 0
    for pattern in PII_PATTERNS:
        matches = list(pattern.finditer(redacted))
        if matches:
            redaction_count += len(matches)
            redacted = pattern.sub(REDACTION_TOKEN, redacted)
    return redacted, redaction_count
