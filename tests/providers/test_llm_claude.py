import httpx
import pytest
import respx

from backend.providers.llm_claude import ClaudeProvider
from backend.services.exceptions import ProviderUnavailableError


@pytest.mark.asyncio
@respx.mock
async def test_complete_returns_text_response() -> None:
    respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "model": "claude-sonnet-5",
                "content": [{"type": "text", "text": "Great job practicing today!"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 10, "output_tokens": 5},
            },
        )
    )
    provider = ClaudeProvider(api_key="sk-ant-test")

    result = await provider.complete(
        messages=[{"role": "user", "content": "I go to work yesterday"}],
        system="You are an English tutor.",
        max_tokens=100,
    )

    assert result == "Great job practicing today!"


@pytest.mark.asyncio
@respx.mock
async def test_complete_raises_domain_error_on_api_failure() -> None:
    respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(500, json={"error": {"message": "boom"}})
    )
    provider = ClaudeProvider(api_key="sk-ant-test")

    with pytest.raises(ProviderUnavailableError):
        await provider.complete(messages=[{"role": "user", "content": "hi"}], system="sys")
