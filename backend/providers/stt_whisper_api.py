from openai import AsyncOpenAI

from backend.providers.base import STTProvider, Transcript
from backend.services.exceptions import ProviderUnavailableError


class WhisperAPIProvider(STTProvider):
    """STT vía OpenAI Whisper API. Requiere OPENAI_API_KEY (no es software libre)."""

    def __init__(self, api_key: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)

    async def transcribe(self, audio: bytes) -> Transcript:
        try:
            result = await self._client.audio.transcriptions.create(
                model="whisper-1",
                file=("audio.webm", audio),
                response_format="verbose_json",
                timestamp_granularities=["word"],
            )
        except Exception as exc:
            raise ProviderUnavailableError(f"Whisper API no disponible: {exc}") from exc

        words = [
            {"w": w.word, "start": w.start, "end": w.end} for w in (result.words or [])
        ]
        # wpm/fillers los calcula services/acoustic.py a partir de `words`, no el provider.
        return Transcript(text=result.text, wpm=0.0, words=words)
