import httpx

from backend.providers.base import LLMProvider
from backend.services.exceptions import ProviderUnavailableError


class OllamaProvider(LLMProvider):
    """LLM local vía Ollama (Apache 2.0). Software libre — provider por defecto."""

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def complete(
        self, messages: list[dict], system: str, max_tokens: int = 400
    ) -> str:
        payload = {
            "model": self._model,
            "messages": [{"role": "system", "content": system}, *messages],
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(f"{self._base_url}/api/chat", json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError(f"Ollama no disponible: {exc}") from exc
        return response.json()["message"]["content"]
