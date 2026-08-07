import json

import pytest

from backend.providers.base import LLMProvider
from backend.services.exceptions import ProviderUnavailableError
from backend.services.translate import get_translation_practice


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
async def test_get_translation_practice_returns_english_and_notes() -> None:
    """Fase C del plan de mejora (comparación vs Loora): a diferencia de
    los 30 modismos curados (fijos), esto deja que el alumno pida
    vocabulario que nace de lo que ÉL quiere decir, no de una lista
    prearmada — mismo concepto que la herramienta de traducción de Loora."""
    llm = _CapturingLLM(
        json.dumps(
            {
                "english": "I'm running a bit late, sorry!",
                "notes": "Uso informal y común para avisar que vas a llegar tarde.",
            }
        )
    )

    result = await get_translation_practice(llm, spanish_text="Voy a llegar un poco tarde")

    assert result["english"] == "I'm running a bit late, sorry!"
    assert "informal" in result["notes"]


@pytest.mark.asyncio
async def test_get_translation_practice_sends_spanish_text_to_llm() -> None:
    llm = _CapturingLLM(json.dumps({"english": "x", "notes": "y"}))

    await get_translation_practice(llm, spanish_text="Necesito ayuda")

    assert "Necesito ayuda" in llm.last_messages[0]["content"]


@pytest.mark.asyncio
async def test_get_translation_practice_raises_when_llm_returns_invalid_json() -> None:
    llm = _CapturingLLM("esto no es json")

    with pytest.raises(ProviderUnavailableError):
        await get_translation_practice(llm, spanish_text="hola")


@pytest.mark.asyncio
async def test_get_translation_practice_raises_when_english_missing() -> None:
    llm = _CapturingLLM(json.dumps({"notes": "y"}))

    with pytest.raises(ProviderUnavailableError):
        await get_translation_practice(llm, spanish_text="hola")


@pytest.mark.asyncio
async def test_get_translation_practice_defaults_notes_to_empty_string() -> None:
    llm = _CapturingLLM(json.dumps({"english": "Hello"}))

    result = await get_translation_practice(llm, spanish_text="Hola")

    assert result["notes"] == ""


def test_system_prompt_requires_english_output() -> None:
    from backend.services.translate import SYSTEM_PROMPT

    assert "inglés" in SYSTEM_PROMPT.lower()
