import httpx
import pytest
import respx

from backend.providers.stt_whisper_api import WhisperAPIProvider
from backend.services.exceptions import ProviderUnavailableError


@pytest.mark.asyncio
@respx.mock
async def test_transcribe_returns_text_and_word_timestamps() -> None:
    respx.post("https://api.openai.com/v1/audio/transcriptions").mock(
        return_value=httpx.Response(
            200,
            json={
                "task": "transcribe",
                "language": "english",
                "duration": 1.2,
                "text": "hello world",
                "words": [
                    {"word": "hello", "start": 0.0, "end": 0.4},
                    {"word": "world", "start": 0.5, "end": 0.9},
                ],
                "segments": [],
            },
        )
    )
    provider = WhisperAPIProvider(api_key="sk-test")

    result = await provider.transcribe(b"fake-audio-bytes")

    assert result.text == "hello world"
    assert result.words == [
        {"w": "hello", "start": 0.0, "end": 0.4},
        {"w": "world", "start": 0.5, "end": 0.9},
    ]
    assert result.wpm == 0.0  # lo calcula acoustic.py, no el provider


@pytest.mark.asyncio
@respx.mock
async def test_transcribe_raises_domain_error_on_api_failure() -> None:
    respx.post("https://api.openai.com/v1/audio/transcriptions").mock(
        return_value=httpx.Response(500, json={"error": {"message": "boom"}})
    )
    provider = WhisperAPIProvider(api_key="sk-test")

    with pytest.raises(ProviderUnavailableError):
        await provider.transcribe(b"fake-audio-bytes")
