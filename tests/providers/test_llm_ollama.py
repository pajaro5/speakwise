import httpx
import pytest
import respx

from backend.providers.llm_ollama import OllamaProvider
from backend.services.exceptions import ProviderUnavailableError


@pytest.mark.asyncio
@respx.mock
async def test_complete_returns_text_response() -> None:
    respx.post("http://ollama:11434/api/chat").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "qwen2.5:7b",
                "message": {"role": "assistant", "content": "Great job practicing today!"},
                "done": True,
            },
        )
    )
    provider = OllamaProvider(base_url="http://ollama:11434", model="qwen2.5:7b")

    result = await provider.complete(
        messages=[{"role": "user", "content": "I go to work yesterday"}],
        system="You are an English tutor.",
    )

    assert result == "Great job practicing today!"


@pytest.mark.asyncio
@respx.mock
async def test_complete_raises_domain_error_when_ollama_down() -> None:
    respx.post("http://ollama:11434/api/chat").mock(
        return_value=httpx.Response(500, json={"error": "model not found"})
    )
    provider = OllamaProvider(base_url="http://ollama:11434", model="qwen2.5:7b")

    with pytest.raises(ProviderUnavailableError):
        await provider.complete(messages=[{"role": "user", "content": "hi"}], system="sys")
