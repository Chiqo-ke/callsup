from __future__ import annotations

import json

import httpx
from fastapi.testclient import TestClient

from callsup_intelligence_engine.main import create_app


def _mock_llm_transport(request: httpx.Request) -> httpx.Response:
    payload = json.loads(request.content.decode("utf-8"))
    prompt = payload.get("prompt", "")
    if "Generate concise call summary" in prompt:
        body = {"text": "Customer requested balance support.", "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20}}
    else:
        body = {"text": json.dumps({"account_last4": "4321"}), "usage": {"prompt_tokens": 14, "completion_tokens": 7, "total_tokens": 21}}
    return httpx.Response(status_code=200, json=body)


def main() -> None:
    from callsup_intelligence_engine.core.audit import AuditStore
    from callsup_intelligence_engine.core.conversation import ConversationLogStore, ConversationService
    from callsup_intelligence_engine.core.llm_adapter import LLMAdapterClient
    from callsup_intelligence_engine.core.verification import TransactionVerifier

    async_client = httpx.AsyncClient(
        transport=httpx.MockTransport(_mock_llm_transport),
        base_url="http://svc-llm-adapter",
    )
    service = ConversationService(
        llm_client=LLMAdapterClient(base_url="http://svc-llm-adapter", http_client=async_client),
        audit_store=AuditStore(),
        verifier=TransactionVerifier(),
        logs=ConversationLogStore(),
    )
    with TestClient(create_app(service)) as client:
        result = client.post(
            "/intelligence/e2e-demo",
            json={
                "business_id": "biz-001",
                "conv_id": "conv-demo",
                "audio_text": "My email is a@b.com and my phone is 555-111-2222, what is my balance?",
            },
        )
        result.raise_for_status()
        payload = result.json()
        print("E2E stages:", json.dumps(payload["stages"], indent=2))
        print("Stored redacted transcript:", json.dumps(payload["redacted_transcript"], indent=2))


if __name__ == "__main__":
    main()
