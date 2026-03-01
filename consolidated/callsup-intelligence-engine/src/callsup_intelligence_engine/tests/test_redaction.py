from callsup_intelligence_engine.core.redaction import REDACTION_TOKEN, redact_pii


def test_redact_pii_masks_sensitive_values() -> None:
    text = "Email me at user@example.com or call 555-123-4567 with SSN 123-45-6789."
    redacted, count = redact_pii(text)
    assert REDACTION_TOKEN in redacted
    assert "user@example.com" not in redacted
    assert "555-123-4567" not in redacted
    assert "123-45-6789" not in redacted
    assert count >= 3
