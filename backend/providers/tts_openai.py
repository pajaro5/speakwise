from openai import AsyncOpenAI

from backend.providers.base import TTSProvider
from backend.services.exceptions import ProviderUnavailableError


class OpenAITTSProvider(TTSProvider):
    """TTS vía OpenAI API. Requiere OPENAI_API_KEY (no es software libre)."""

    def __init__(self, api_key: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)

    async def synthesize(self, text: str, voice: str = "default") -> bytes:
        voice_name = "alloy" if voice == "default" else voice
        try:
            response = await self._client.audio.speech.create(
                model="tts-1",
                voice=voice_name,
                input=text,
            )
        except Exception as exc:
            raise ProviderUnavailableError(f"OpenAI TTS no disponible: {exc}") from exc
        return response.content
