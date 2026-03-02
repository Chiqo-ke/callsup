import json

from callsup_intelligence_engine.core.verification import TransactionVerifier


def test_transaction_verification_and_rendering_success() -> None:
    verifier = TransactionVerifier()
    output = json.dumps({"account_last4": "4321"})
    result = verifier.verify_and_render("biz-001", "balance_inquiry", output)
    assert result.ok is True
    assert "account ending 4321" in result.response_text
    assert "$120.45" in result.response_text


def test_transaction_verification_fails_for_unknown_account() -> None:
    verifier = TransactionVerifier()
    output = json.dumps({"account_last4": "1111"})
    result = verifier.verify_and_render("biz-001", "balance_inquiry", output)
    assert result.ok is False
