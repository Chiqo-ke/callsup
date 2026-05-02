"""
End-to-end test for the callsup escalation pipeline.

Tests:
  1. Health checks on audio engine (8010) and LLM adapter (9100)
  2. LLM adapter tool-calling: escalation phrase → returns create_escalation_ticket tool_call
  3. LLM adapter tool-calling: normal phrase → returns no tool_call
  4. Keyword fallback in audio engine: send voice_chat with escalation reply
  5. GET /escalation-queue returns ticket created in step 4

Usage:
  cd c:\\Users\\nyaga\\Documents\\callsup
  python test_escalation_e2e.py
"""
from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import requests

# ── Config ──────────────────────────────────────────────────────────────────────
AUDIO_BASE   = "http://127.0.0.1:8010"
ADAPTER_BASE = "http://127.0.0.1:9100"

# Known test user (Techco)
JWT_SECRET   = "callsup-dev-secret-change-in-production"
JWT_ALGO     = "HS256"
USER_ID      = "a26dccdc-9f47-4503-a45b-b7bea4b9ecb1"
USERNAME     = "Techco"
BUSINESS_ID  = "e776a10e-afc6-41e2-a7bf-244a494adf70"

# ── Helpers ─────────────────────────────────────────────────────────────────────
PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"

results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> bool:
    status = PASS if condition else FAIL
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    results.append((name, condition, detail))
    return condition


def make_jwt() -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": USER_ID,
        "username": USERNAME,
        "business_id": BUSINESS_ID,
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def auth_headers() -> dict:
    return {"Authorization": f"Bearer {make_jwt()}"}


# ── Test 1: Health checks ────────────────────────────────────────────────────────
print("\n=== Test 1: Health Checks ===")
try:
    r = requests.get(f"{AUDIO_BASE}/health", timeout=5)
    check("Audio engine health", r.status_code == 200, f"status={r.status_code}")
except Exception as e:
    check("Audio engine health", False, f"ERROR: {e}")

try:
    r = requests.get(f"{ADAPTER_BASE}/health", timeout=5)
    data = r.json()
    check("LLM adapter health", r.status_code == 200, f"backend={data.get('backend')}")
except Exception as e:
    check("LLM adapter health", False, f"ERROR: {e}")


# ── Test 2: LLM adapter returns tool_call for escalation phrase ──────────────────
print("\n=== Test 2: LLM Adapter — Escalation Phrase → Tool Call ===")
ESCALATION_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_escalation_ticket",
        "description": "Create a task queue entry to transfer the caller to a human support agent.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason":   {"type": "string"},
                "priority": {"type": "string", "enum": ["high", "medium", "low"]},
            },
            "required": ["reason", "priority"],
        },
    },
}
payload_esc = {
    "prompt": (
        "The AI agent just said to the caller: "
        "'I am now transferring you to a human agent, please hold the line.'\n"
        "Does this reply indicate the caller is being transferred to a human agent? "
        "If yes, call create_escalation_ticket."
    ),
    "system_prompt": "Evaluate whether the agent reply implies escalation to a human.",
    "tools": [ESCALATION_TOOL_SCHEMA],
    "tool_choice": "auto",
}
try:
    r = requests.post(f"{ADAPTER_BASE}/v1/generate", json=payload_esc, timeout=30)
    check("Adapter /v1/generate 200", r.status_code == 200, f"status={r.status_code}")
    data = r.json()
    tool_calls = data.get("tool_calls") or []
    has_tc = bool(tool_calls)
    check("Adapter returns tool_calls for escalation phrase", has_tc,
          f"tool_calls={json.dumps(tool_calls)[:120]}")
    if has_tc:
        fn = tool_calls[0].get("function", {})
        check("Tool call name is create_escalation_ticket",
              fn.get("name") == "create_escalation_ticket",
              f"got: {fn.get('name')}")
        args_raw = fn.get("arguments", "{}")
        args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
        check("Tool call has 'reason' arg", "reason" in args, str(args))
        check("Tool call has 'priority' arg", "priority" in args, str(args))
except Exception as e:
    check("Adapter tool call request", False, f"ERROR: {e}")


# ── Test 3: LLM adapter returns NO tool_call for normal phrase ───────────────────
print("\n=== Test 3: LLM Adapter — Normal Phrase → No Tool Call ===")
payload_normal = {
    "prompt": (
        "The AI agent just said to the caller: "
        "'I can help you with that. Your balance is $120.'\n"
        "Does this reply indicate the caller is being transferred to a human agent?"
    ),
    "system_prompt": "Evaluate whether the agent reply implies escalation to a human.",
    "tools": [ESCALATION_TOOL_SCHEMA],
    "tool_choice": "auto",
}
try:
    r = requests.post(f"{ADAPTER_BASE}/v1/generate", json=payload_normal, timeout=30)
    check("Adapter /v1/generate 200", r.status_code == 200, f"status={r.status_code}")
    data = r.json()
    tool_calls = data.get("tool_calls") or []
    check("No tool_call for normal phrase", not bool(tool_calls),
          f"tool_calls={json.dumps(tool_calls)[:120]}")
except Exception as e:
    check("Adapter normal phrase request", False, f"ERROR: {e}")


# ── Test 4: Voice chat with escalation reply creates ticket ──────────────────────
print("\n=== Test 4: Voice Chat → Escalation Ticket Created ===")
conv_id = f"test-esc-{uuid.uuid4().hex[:8]}"
ticket_id_created: str | None = None

# First turn to initialise session
try:
    r = requests.post(
        f"{AUDIO_BASE}/audio/voice/chat",
        json={
            "conv_id": conv_id,
            "business_id": BUSINESS_ID,
            "message": "",
            "history": [],
            "first_turn": True,
        },
        headers=auth_headers(),
        timeout=30,
    )
    check("First turn 200", r.status_code == 200, f"status={r.status_code}")
except Exception as e:
    check("First turn request", False, f"ERROR: {e}")

# Second turn: caller asks for a human agent
try:
    r = requests.post(
        f"{AUDIO_BASE}/audio/voice/chat",
        json={
            "conv_id": conv_id,
            "business_id": BUSINESS_ID,
            "message": (
                "I've confirmed I'm interested in a partnership — "
                "can I speak to a real human agent now?"
            ),
            "history": [],
            "first_turn": False,
        },
        headers=auth_headers(),
        timeout=60,
    )
    check("Escalation turn 200", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        data = r.json()
        escalated = data.get("escalated", False)
        check("voice_chat returned escalated=True", escalated, f"reply={data.get('reply','')[:120]}")
except Exception as e:
    check("Escalation turn request", False, f"ERROR: {e}")


# ── Test 5: GET /escalation-queue shows the ticket ──────────────────────────────
print("\n=== Test 5: GET /escalation-queue ===")
try:
    r = requests.get(
        f"{AUDIO_BASE}/escalation-queue",
        headers=auth_headers(),
        timeout=10,
    )
    check("GET /escalation-queue 200", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        tickets = r.json()
        check("Response is a list", isinstance(tickets, list), f"type={type(tickets).__name__}")
        if isinstance(tickets, list):
            check("Queue has at least one ticket", len(tickets) > 0, f"count={len(tickets)}")
            if tickets:
                latest = tickets[-1]
                check("Ticket has id field", "id" in latest, str(list(latest.keys())))
                check("Ticket has business_id", latest.get("business_id") == BUSINESS_ID,
                      f"got={latest.get('business_id')}")
                check("Ticket has reason", bool(latest.get("reason")),
                      f"reason={latest.get('reason')}")
except Exception as e:
    check("GET /escalation-queue", False, f"ERROR: {e}")


# ── Direct queue creation test (fallback if voice_chat needs OpenCode) ───────────
print("\n=== Test 6: POST /escalation-queue (direct ticket creation) ===")
try:
    r = requests.post(
        f"{AUDIO_BASE}/escalation-queue",
        json={
            "session_id": f"direct-test-{uuid.uuid4().hex[:8]}",
            "reason": "E2E direct creation test",
            "priority": "low",
        },
        headers=auth_headers(),
        timeout=10,
    )
    check("POST /escalation-queue 200/201", r.status_code in (200, 201), f"status={r.status_code}")
    if r.status_code in (200, 201):
        ticket = r.json()
        check("Ticket id present", bool(ticket.get("id")), str(ticket.get("id")))
        check("Ticket reason correct", ticket.get("reason") == "E2E direct creation test",
              f"got={ticket.get('reason')}")
except Exception as e:
    check("POST /escalation-queue", False, f"ERROR: {e}")


# ── Summary ──────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
total  = len(results)
passed = sum(1 for _, ok, _ in results if ok)
failed = total - passed
print(f"Results: {passed}/{total} passed")
if failed:
    print(f"\nFailed checks:")
    for name, ok, detail in results:
        if not ok:
            print(f"  - {name}" + (f": {detail}" if detail else ""))
print("=" * 60)
sys.exit(0 if failed == 0 else 1)
