import base64
import hashlib
import re
from typing import Any

from cryptography.fernet import Fernet


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")


def redact_text(text: str) -> str:
    redacted = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    redacted = PHONE_RE.sub("[REDACTED_PHONE]", redacted)
    return redacted


def redact_payload(payload: Any) -> Any:
    if isinstance(payload, str):
        return redact_text(payload)
    if isinstance(payload, list):
        return [redact_payload(item) for item in payload]
    if isinstance(payload, dict):
        return {key: redact_payload(value) for key, value in payload.items()}
    return payload


def _fernet_from_vault_ref(vault_ref: str) -> Fernet:
    digest = hashlib.sha256(vault_ref.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_at_rest(vault_ref: str, plaintext: str | None) -> bytes | None:
    if plaintext is None:
        return None
    return _fernet_from_vault_ref(vault_ref).encrypt(plaintext.encode("utf-8"))


def decrypt_at_rest(vault_ref: str, ciphertext: bytes | None) -> str | None:
    if ciphertext is None:
        return None
    return _fernet_from_vault_ref(vault_ref).decrypt(ciphertext).decode("utf-8")

