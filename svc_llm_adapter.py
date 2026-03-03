"""Mock svc-llm-adapter — returns realistic fake LLM responses for smoke testing."""
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="svc-llm-adapter (mock)", version="0.1.0")


class GenerateRequest(BaseModel):
    prompt: str
    model: str = "gpt-4.1-mini"


class GenerateResponse(BaseModel):
    text: str
    usage: dict


MOCK_RESPONSES = [
    "Thank you for contacting support. I understand you need help with your account. I will escalate this to a specialist.",
    "I can see the issue you are describing. The resolution time is typically 24 hours.",
    "Your case has been logged and assigned reference number CS-20260302-001.",
]


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0-mock"}


@app.post("/v1/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    # Rotate through canned responses based on prompt length
    idx = len(req.prompt) % len(MOCK_RESPONSES)
    text = MOCK_RESPONSES[idx]
    tokens = len(req.prompt.split())
    return GenerateResponse(
        text=text,
        usage={
            "prompt_tokens": tokens,
            "completion_tokens": len(text.split()),
            "total_tokens": tokens + len(text.split()),
        },
    )
