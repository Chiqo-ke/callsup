from __future__ import annotations

import json

import httpx
from fastapi.testclient import TestClient

from callsup_intelligence_engine.core.audit import AuditStore
from callsup_intelligence_engine.core.conversation import ConversationLogStore, ConversationService
from callsup_intelligence_engine.core.llm_adapter import LLMAdapterClient
from callsup_intelligence_engine.core.verification import TransactionVerifier
from callsup_intelligence_engine.main import create_app


def _mock_llm_transport(request: httpx.Request) -> httpx.Response:
    payload = json.loads(request.content.decode("utf-8"))
    prompt = payload.get("prompt", "")
    if "Generate concise call summary" in prompt:
        body = {"text": "Customer asked for account help.", "usage": {"prompt_tokens": 10, "completion_tokens": 6, "total_tokens": 16}}
    elif "balance_inquiry" in prompt:
        body = {"text": json.dumps({"account_last4": "4321"}), "usage": {"prompt_tokens": 14, "completion_tokens": 7, "total_tokens": 21}}
    else:
        body = {"text": "General support response", "usage": {"prompt_tokens": 8, "completion_tokens": 6, "total_tokens": 14}}
    return httpx.Response(status_code=200, json=body)


def build_test_client() -> TestClient:
    transport = httpx.MockTransport(_mock_llm_transport)
    http_client = httpx.AsyncClient(transport=transport, base_url="http://svc-llm-adapter")
    service = ConversationService(
        llm_client=LLMAdapterClient(base_url="http://svc-llm-adapter", http_client=http_client),
        audit_store=AuditStore(),
        verifier=TransactionVerifier(),
        logs=ConversationLogStore(),
    )
    return TestClient(create_app(service))


def test_step_endpoint_redacts_and_verifies_transaction() -> None:
    with build_test_client() as client:
        response = client.post(
            "/intelligence/step",
            json={
                "business_id": "biz-001",
                "conv_id": "conv-001",
                "segment": {
                    "event": "transcript.segment",
                    "business_id": "biz-001",
                    "conv_id": "conv-001",
                    "segment_id": "seg-1",
                    "speaker": "customer",
                    "start_ts": "2026-01-01T00:00:00Z",
                    "end_ts": "2026-01-01T00:00:02Z",
                    "text": "My email is user@example.com and I need my balance.",
                    "confidence": 0.95,
                },
                "session_state": {},
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["verification_passed"] is True
        assert payload["action_type"] == "transactional_response"
        assert "account ending 4321" in payload["response_text"]


def test_e2e_demo_returns_redacted_transcript() -> None:
    with build_test_client() as client:
        response = client.post(
            "/intelligence/e2e-demo",
            json={
                "business_id": "biz-001",
                "conv_id": "conv-e2e",
                "audio_text": "Call me at 555-123-4567 and check my balance.",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        transcript = payload["redacted_transcript"]
        assert transcript
        assert "555-123-4567" not in transcript[0]["text_redacted"]
