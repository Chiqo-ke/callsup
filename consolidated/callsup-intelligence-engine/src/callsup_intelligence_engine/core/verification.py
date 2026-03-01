from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class VerificationResult:
    ok: bool
    response_text: str


class TransactionVerifier:
    def __init__(self) -> None:
        self.templates = {
            "balance_inquiry": "Your balance for account ending {account_last4} is ${balance}.",
            "payment": "Payment of ${amount} was scheduled for account ending {account_last4}.",
        }
        self.db = {
            "biz-001": {
                "accounts": {
                    "4321": {"balance": "120.45"},
                    "9999": {"balance": "401.00"},
                }
            }
        }

    def verify_and_render(self, business_id: str, intent: str, llm_text: str) -> VerificationResult:
        if intent not in self.templates:
            return VerificationResult(ok=True, response_text=llm_text)
        try:
            payload: dict[str, Any] = json.loads(llm_text)
        except json.JSONDecodeError:
            return VerificationResult(ok=False, response_text="Unable to verify transactional output.")

        account_last4 = str(payload.get("account_last4", ""))
        account_data = (
            self.db.get(business_id, {})
            .get("accounts", {})
            .get(account_last4)
        )
        if not account_data:
            return VerificationResult(ok=False, response_text="Unable to verify transactional output.")

        template = self.templates[intent]
        if intent == "balance_inquiry":
            rendered = template.format(account_last4=account_last4, balance=account_data["balance"])
            return VerificationResult(ok=True, response_text=rendered)
        amount = str(payload.get("amount", ""))
        if not amount:
            return VerificationResult(ok=False, response_text="Unable to verify transactional output.")
        rendered = template.format(account_last4=account_last4, amount=amount)
        return VerificationResult(ok=True, response_text=rendered)
