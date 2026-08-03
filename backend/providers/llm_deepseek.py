from openai import AsyncOpenAI

from backend.providers.base import LLMProvider
from backend.services.exceptions import ProviderUnavailableError

DEFAULT_MODEL = "deepseek-chat"
BASE_URL = "https://api.deepseek.com"


class DeepSeekProvider(LLMProvider):
    """LLM vía DeepSeek API (compatible con el SDK de OpenAI).

    No es software libre, pero es la alternativa paga más económica frente a
    Claude/GPT para este caso de uso — usar cuando Ollama local no alcance.
    """

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=BASE_URL)
        self._model = model

    async def complete(
        self, messages: list[dict], system: str, max_tokens: int = 400
    ) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=[{"role": "system", "content": system}, *messages],
            )
        except Exception as exc:
            raise ProviderUnavailableError(f"DeepSeek API no disponible: {exc}") from exc
        return response.choices[0].message.content or ""
