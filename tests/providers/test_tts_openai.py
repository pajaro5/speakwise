import httpx
import pytest
import respx

from backend.providers.tts_openai import OpenAITTSProvider
from backend.services.exceptions import ProviderUnavailableError


@pytest.mark.asyncio
@respx.mock
async def test_synthesize_returns_audio_bytes() -> None:
    respx.post("https://api.openai.com/v1/audio/speech").mock(
        return_value=httpx.Response(
            200, content=b"FAKE-MP3-BYTES", headers={"content-type": "audio/mpeg"}
        )
    )
    provider = OpenAITTSProvider(api_key="sk-test")

    result = await provider.synthesize("hello there")

    assert result == b"FAKE-MP3-BYTES"


@pytest.mark.asyncio
@respx.mock
async def test_synthesize_raises_domain_error_when_api_down() -> None:
    respx.post("https://api.openai.com/v1/audio/speech").mock(
        return_value=httpx.Response(503, json={"error": {"message": "down"}})
    )
    provider = OpenAITTSProvider(api_key="sk-test")

    with pytest.raises(ProviderUnavailableError):
        await provider.synthesize("hello there")
