from callsup_platform.config import Settings
from callsup_platform.security import decrypt_at_rest, encrypt_at_rest, redact_payload, redact_text


def test_redaction_masks_email_and_phone():
    text = "Contact me at jane.doe@example.com or +1 (555) 123-4567"
    redacted = redact_text(text)
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_PHONE]" in redacted


def test_redact_payload_nested():
    payload = {"a": "foo@example.com", "b": ["+44 203 000 1111", {"c": "safe"}]}
    redacted = redact_payload(payload)
    assert redacted["a"] == "[REDACTED_EMAIL]"
    assert redacted["b"][0] == "[REDACTED_PHONE]"
    assert redacted["b"][1]["c"] == "safe"


def test_encryption_round_trip():
    ref = "vault://kv/data/callsup/platform/encryption"
    encrypted = encrypt_at_rest(ref, "rules")
    assert encrypted != b"rules"
    assert decrypt_at_rest(ref, encrypted) == "rules"


def test_settings_reject_non_vault_secret_reference():
    try:
        Settings(callsup_platform_vault_encryption_key_ref="plain-secret")
        assert False, "Expected settings validation to fail"
    except Exception as exc:
        assert "Vault-only secret references are required" in str(exc)

