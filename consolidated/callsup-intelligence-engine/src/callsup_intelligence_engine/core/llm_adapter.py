from __future__ import annotations

from typing import Any

import httpx


class LLMAdapterClient:
    """Local svc-llm-adapter contract client."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 10.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = http_client or httpx.AsyncClient(timeout=timeout)

    async def generate(self, prompt_redacted: str, model: str) -> dict[str, Any]:
        payload = {"prompt": prompt_redacted, "model": model}
        response = await self._client.post(f"{self.base_url}/v1/generate", json=payload)
        response.raise_for_status()
        data = response.json()
        return {
            "text": data.get("text", ""),
            "usage": {
                "prompt_tokens": int(data.get("usage", {}).get("prompt_tokens", 0)),
                "completion_tokens": int(data.get("usage", {}).get("completion_tokens", 0)),
                "total_tokens": int(data.get("usage", {}).get("total_tokens", 0)),
            },
        }

    async def close(self) -> None:
        await self._client.aclose()
