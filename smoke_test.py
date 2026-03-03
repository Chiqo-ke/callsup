"""
CALLSUP Full E2E Smoke Test
Tests: Mock LLM Adapter (:9100) → Audio Engine (:8010) → Intelligence Engine (:8011)
Business scenario: customer calls about a payment and refund.
"""
import io
import json
import sys
import urllib.request
import urllib.error

ADAPTER_URL   = "http://127.0.0.1:9100"
AUDIO_URL     = "http://127.0.0.1:8010"
INTEL_URL     = "http://127.0.0.1:8011"

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
STEP = "\033[94m[STEP]\033[0m"


def request_json(method, url, body=None, headers=None):
    data = json.dumps(body).encode() if body else None
    h = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def multipart_post(url, fields, file_field, filename, file_bytes):
    """Minimal multipart/form-data POST without external deps."""
    boundary = "---CallsupSmokeBoundary123"
    body_parts = []
    for k, v in fields.items():
        body_parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n"
        )
    body_parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; filename=\"{filename}\"\r\n"
        f"Content-Type: application/octet-stream\r\n\r\n"
    )
    raw = "".join(body_parts).encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        url, data=raw, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


errors = []

# ── 1. Health checks ──────────────────────────────────────────────────────────
print(f"\n{STEP} 1. Health checks")
for label, url in [
    ("Mock LLM Adapter", f"{ADAPTER_URL}/health"),
    ("Audio Engine",     f"{AUDIO_URL}/health"),
    ("Intelligence Engine", f"{INTEL_URL}/health"),
]:
    try:
        r = request_json("GET", url)
        print(f"  {PASS} {label}: {r}")
    except Exception as e:
        print(f"  {FAIL} {label}: {e}")
        errors.append(f"{label} health failed")

# ── 2. Mock LLM adapter: direct generate call ─────────────────────────────────
print(f"\n{STEP} 2. Mock LLM adapter — direct /v1/generate")
try:
    r = request_json("POST", f"{ADAPTER_URL}/v1/generate", {
        "prompt": "Customer: I need to pay my bill.",
        "model": "gpt-4.1-mini"
    })
    print(f"  {PASS} response_text: {r['text']}")
    print(f"  {PASS} tokens: {r['usage']}")
except Exception as e:
    print(f"  {FAIL} {e}")
    errors.append("LLM generate failed")

# ── 3. Audio Engine: ingest a call ───────────────────────────────────────────
print(f"\n{STEP} 3. Audio Engine — ingest customer call (with PII)")
CALL_TEXT = (
    "Hi, I want to pay my outstanding balance. "
    "My card number is 4111111111111111 and my email is customer@acmecorp.com."
)
try:
    r = multipart_post(
        f"{AUDIO_URL}/audio/ingest",
        fields={"business_id": "acme-corp", "conv_id": "call-001"},
        file_field="file",
        filename="call_audio.wav",
        file_bytes=CALL_TEXT.encode(),
    )
    print(f"  {PASS} ingest response: {r}")
except Exception as e:
    print(f"  {FAIL} {e}")
    errors.append("Audio ingest failed")

# ── 4. Audio Engine: retrieve transcript ──────────────────────────────────────
print(f"\n{STEP} 4. Audio Engine — retrieve transcript (PII should be redacted)")
try:
    r = request_json("GET", f"{AUDIO_URL}/audio/transcript/call-001")
    segments = r.get("segments", r) if isinstance(r, dict) else r
    for seg in (segments if isinstance(segments, list) else [segments])[:2]:
        text = seg.get("text", str(seg))
        pii_leaked = "4111111111111111" in text or "customer@acmecorp.com" in text
        status = FAIL if pii_leaked else PASS
        print(f"  {status} segment text: {text}")
        if pii_leaked:
            errors.append("PII leaked in transcript!")
except Exception as e:
    print(f"  {FAIL} {e}")
    errors.append("Transcript fetch failed")

# ── 5. Intelligence Engine: e2e-demo ─────────────────────────────────────────
print(f"\n{STEP} 5. Intelligence Engine — /intelligence/e2e-demo")
try:
    r = request_json("POST", f"{INTEL_URL}/intelligence/e2e-demo", {
        "business_id": "acme-corp",
        "conv_id": "call-002",
        "audio_text": "I need a refund on my recent payment. The amount was charged twice."
    })
    for key in ("ingest", "asr", "nlu", "action", "retrieval", "summary"):
        val = r.get(key)
        status = PASS if val is not None else FAIL
        print(f"  {status} {key}: {val}")
except Exception as e:
    print(f"  {FAIL} {e}")
    errors.append("e2e-demo failed")

# ── 6. Intelligence Engine: single step ──────────────────────────────────────
print(f"\n{STEP} 6. Intelligence Engine — /intelligence/step (single segment)")
from datetime import datetime, timezone, timedelta
now = datetime.now(timezone.utc).isoformat()
end = (datetime.now(timezone.utc) + timedelta(seconds=4)).isoformat()
try:
    r = request_json("POST", f"{INTEL_URL}/intelligence/step", {
        "business_id": "acme-corp",
        "conv_id": "call-003",
        "segment": {
            "business_id": "acme-corp",
            "conv_id": "call-003",
            "segment_id": "seg-001",
            "speaker": "customer",
            "start_ts": now,
            "end_ts": end,
            "text": "What is my current balance?",
            "confidence": 0.97
        },
        "session_state": {}
    })
    print(f"  {PASS} intent:       {r.get('nlu_intent')}")
    print(f"  {PASS} action_type:  {r.get('action_type')}")
    print(f"  {PASS} response:     {r.get('response_text')}")
except Exception as e:
    print(f"  {FAIL} {e}")
    errors.append("step endpoint failed")

# ── Result summary ────────────────────────────────────────────────────────────
print("\n" + "="*55)
if errors:
    print(f"{FAIL} SMOKE TEST FAILED — {len(errors)} issue(s):")
    for e in errors:
        print(f"   • {e}")
    sys.exit(1)
else:
    print(f"{PASS} ALL CHECKS PASSED — system is working end-to-end")
print("="*55 + "\n")
