import httpx
import pytest
import respx

from backend.providers.llm_deepseek import DeepSeekProvider
from backend.services.exceptions import ProviderUnavailableError


@pytest.mark.asyncio
@respx.mock
async def test_complete_returns_text_response() -> None:
    respx.post("https://api.deepseek.com/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "chatcmpl-1",
                "object": "chat.completion",
                "model": "deepseek-chat",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "Great job practicing today!"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
        )
    )
    provider = DeepSeekProvider(api_key="sk-deepseek-test")

    result = await provider.complete(
        messages=[{"role": "user", "content": "I go to work yesterday"}],
        system="You are an English tutor.",
    )

    assert result == "Great job practicing today!"


@pytest.mark.asyncio
@respx.mock
async def test_complete_raises_domain_error_on_api_failure() -> None:
    respx.post("https://api.deepseek.com/chat/completions").mock(
        return_value=httpx.Response(500, json={"error": {"message": "boom"}})
    )
    provider = DeepSeekProvider(api_key="sk-deepseek-test")

    with pytest.raises(ProviderUnavailableError):
        await provider.complete(messages=[{"role": "user", "content": "hi"}], system="sys")
