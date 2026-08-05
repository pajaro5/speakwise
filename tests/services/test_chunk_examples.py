import json

import pytest

from backend.providers.base import LLMProvider
from backend.services.chunk_examples import get_chunk_examples
from backend.services.exceptions import ProviderUnavailableError


class _CapturingLLM(LLMProvider):
    def __init__(self, response: str) -> None:
        self.response = response
        self.last_system_prompt: str | None = None
        self.last_messages: list | None = None

    async def complete(self, messages: list, system: str, max_tokens: int = 400) -> str:
        self.last_system_prompt = system
        self.last_messages = messages
        return self.response


@pytest.mark.asyncio
async def test_get_chunk_examples_returns_three_examples() -> None:
    llm = _CapturingLLM(
        json.dumps(
            {
                "sentence": "Be careful with that.",
                "paragraph": "I know this road is tricky. Be careful with that curve "
                "ahead. Slow down before you get there.",
                "conversation": "A: I'm going to fix the wiring myself.\n"
                "B: Be careful with that — turn off the power first.",
            }
        )
    )

    examples = await get_chunk_examples(llm, chunk="Be careful with that.", function="imperative")

    assert set(examples.keys()) == {"sentence", "paragraph", "conversation"}
    assert examples["sentence"]
    assert examples["paragraph"]
    assert examples["conversation"]


@pytest.mark.asyncio
async def test_get_chunk_examples_sends_chunk_and_function_to_llm() -> None:
    llm = _CapturingLLM(json.dumps({"sentence": "x", "paragraph": "y", "conversation": "z"}))

    await get_chunk_examples(llm, chunk="Be careful with that.", function="imperative")

    assert "Be careful with that." in llm.last_messages[0]["content"]
    assert "imperative" in llm.last_messages[0]["content"]


@pytest.mark.asyncio
async def test_get_chunk_examples_raises_when_llm_returns_invalid_json() -> None:
    llm = _CapturingLLM("esto no es json")

    with pytest.raises(ProviderUnavailableError):
        await get_chunk_examples(llm, chunk="Be careful with that.", function="imperative")


@pytest.mark.asyncio
async def test_get_chunk_examples_raises_when_a_field_is_missing() -> None:
    llm = _CapturingLLM(json.dumps({"sentence": "x", "paragraph": "y"}))

    with pytest.raises(ProviderUnavailableError):
        await get_chunk_examples(llm, chunk="Be careful with that.", function="imperative")
