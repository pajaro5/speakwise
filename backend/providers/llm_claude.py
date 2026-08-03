from anthropic import AsyncAnthropic

from backend.providers.base import LLMProvider
from backend.services.exceptions import ProviderUnavailableError

DEFAULT_MODEL = "claude-sonnet-5"


class ClaudeProvider(LLMProvider):
    """LLM vía Anthropic API. Requiere ANTHROPIC_API_KEY (no es software libre)."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def complete(
        self, messages: list[dict], system: str, max_tokens: int = 400
    ) -> str:
        try:
            response = await self._client.messages.create(
                model=self._model,
                system=system,
                max_tokens=max_tokens,
                messages=messages,
            )
        except Exception as exc:
            raise ProviderUnavailableError(f"Claude API no disponible: {exc}") from exc
        return "".join(
            block.text for block in response.content if block.type == "text"
        )
