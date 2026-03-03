"""
svc-llm-adapter — GitHub Copilot LLM backend
Implements POST /v1/generate as expected by callsup-intelligence-engine.

Authentication:
  Run  python auth_github_copilot.py  once.
  It will display a one-time code, open github.com/login/device,
  and on approval save a .copilot_session file next to this repo.
  The adapter reads tokens from that file — no .env editing needed.

Fallback:
  If no session exists, returns mock responses so the rest of the
  system keeps working while you authenticate.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.request
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel

_ENV_FILE     = Path(__file__).parent.parent / ".env"
_SESSION_FILE = Path(__file__).parent.parent / ".copilot_session"
load_dotenv(_ENV_FILE)

logger = logging.getLogger("callsup.llm_adapter")
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")

app = FastAPI(title="svc-llm-adapter (GitHub Copilot)", version="1.0.0")

# ── Token management (reads .copilot_session, refreshes automatically) ────────
_copilot_token: str   = ""
_token_expires_at: float = 0.0


def _load_session() -> dict:
    if _SESSION_FILE.exists():
        try:
            return json.loads(_SESSION_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _refresh_copilot_token() -> str:
    global _copilot_token, _token_expires_at
    session     = _load_session()
    oauth_token = session.get("oauth_token", "")
    if not oauth_token:
        return ""
    try:
        req = urllib.request.Request(
            "https://api.github.com/copilot_internal/v2/token",
            headers={
                "Authorization": f"token {oauth_token}",
                "Accept": "application/json",
                "Editor-Version": "vscode/1.85.0",
                "Editor-Plugin-Version": "copilot/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        _copilot_token   = data.get("token", "")
        exp_str          = data.get("expires_at", "")
        if exp_str:
            import datetime
            dt = datetime.datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
            _token_expires_at = dt.timestamp() - 60   # refresh 60 s early
        else:
            _token_expires_at = time.time() + 1700    # ~28 min default
        # Persist refreshed token back to session file
        session["copilot_token"]   = _copilot_token
        session["copilot_expires"] = exp_str
        _SESSION_FILE.write_text(json.dumps(session, indent=2), encoding="utf-8")
        logger.info("Copilot token refreshed, valid until %s", exp_str)
    except Exception as exc:
        logger.warning("Copilot token refresh failed: %s", exc)
    return _copilot_token


def _get_copilot_token() -> str:
    global _copilot_token, _token_expires_at
    # Reload session file in case auth script ran after adapter started
    session = _load_session()
    if not _copilot_token:
        _copilot_token = session.get("copilot_token", "")
    if _copilot_token and time.time() < _token_expires_at:
        return _copilot_token
    return _refresh_copilot_token()


# ── API schemas ───────────────────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    prompt: str
    model: str = "gpt-4o"


class GenerateResponse(BaseModel):
    text: str
    usage: dict


# ── Fallback mock (used when not yet authenticated) ───────────────────────────
def _mock_response(prompt: str) -> str:
    p = prompt.lower()
    if "refund" in p:
        return "Refund requests are reviewed within 5 business days. I've logged your request."
    if "balance" in p:
        return "I can help check your balance. Please verify your identity first."
    if "pay" in p:
        return "I can assist with your payment. Please confirm the amount and account."
    if "summary" in p or "summarize" in p:
        return "Call summary: Customer contacted support. Issue resolved. No PII disclosed."
    return "Thank you for contacting support. How can I help you today?"


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    token = _get_copilot_token()
    return {
        "status": "ok",
        "backend": "github-copilot" if token else "mock-fallback",
        "authenticated": bool(token),
    }


@app.post("/v1/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest) -> GenerateResponse:
    token = _get_copilot_token()

    if not token:
        logger.warning("No Copilot token — using mock fallback. Run auth_github_copilot.py to authenticate.")
        text = _mock_response(request.prompt)
        words = len(request.prompt.split())
        return GenerateResponse(
            text=text,
            usage={"prompt_tokens": words, "completion_tokens": len(text.split()), "total_tokens": words + len(text.split())},
        )

    # Real GitHub Copilot call via OpenAI-compatible SDK
    client = OpenAI(
        base_url="https://api.githubcopilot.com",
        api_key=token,
        default_headers={
            "Editor-Version": "vscode/1.85.0",
            "Editor-Plugin-Version": "copilot/1.0",
            "Copilot-Integration-Id": "vscode-chat",
        },
    )
    try:
        completion = client.chat.completions.create(
            model=request.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional call centre AI assistant for a business. "
                        "Be concise, helpful, and never reveal sensitive customer data. "
                        "All PII has already been redacted from the input — do not ask for it."
                    ),
                },
                {"role": "user", "content": request.prompt},
            ],
            max_tokens=256,
            temperature=0.3,
        )
        text = completion.choices[0].message.content or ""
        usage = completion.usage
        return GenerateResponse(
            text=text,
            usage={
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
            },
        )
    except Exception as exc:
        logger.error("Copilot API error: %s", exc)
        raise HTTPException(status_code=502, detail=f"Copilot API error: {exc}") from exc
