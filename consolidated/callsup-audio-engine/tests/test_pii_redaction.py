from app.pii_redaction import redact_text


def test_redact_text_canonical_pii():
    source = (
        "Contact jane@example.com or +1 415-555-0188. "
        "SSN 123-45-6789 and card 4111 1111 1111 1111."
    )
    redacted = redact_text(source)
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_PHONE]" in redacted
    assert "[REDACTED_SSN]" in redacted
    assert "[REDACTED_CARD]" in redacted

