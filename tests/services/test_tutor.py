import pytest

from backend import seed
from backend.database import db_connection
from backend.providers.base import LLMProvider
from backend.services.curriculum import build_todays_plan
from backend.services.tutor import get_tutor_reply


class _CapturingLLM(LLMProvider):
    def __init__(self) -> None:
        self.last_system_prompt: str | None = None

    async def complete(self, messages: list, system: str, max_tokens: int = 400) -> str:
        self.last_system_prompt = system
        return "ok"


@pytest.fixture
def seeded_db_path(tmp_path) -> str:
    db_path = str(tmp_path / "tutor_test.db")
    seed.run(db_path)
    return db_path


@pytest.mark.asyncio
async def test_tutor_system_prompt_includes_todays_chunk(seeded_db_path: str) -> None:
    llm = _CapturingLLM()
    with db_connection(seeded_db_path) as conn:
        plan = build_todays_plan(conn)
        await get_tutor_reply(
            conn, llm,
            text="hello", history=[], session_id=None, topic="", wpm=0.0, fillers=0,
        )

    assert plan["chunk_today"]["chunk"] in llm.last_system_prompt


@pytest.mark.asyncio
async def test_tutor_system_prompt_requires_english_only_replies(seeded_db_path: str) -> None:
    """El tutor mezclaba español en las respuestas — reportado probando la
    sesión completa, contradice el objetivo de práctica de inglés."""
    llm = _CapturingLLM()
    with db_connection(seeded_db_path) as conn:
        await get_tutor_reply(
            conn, llm,
            text="hello", history=[], session_id=None, topic="", wpm=0.0, fillers=0,
        )

    assert "inglés" in llm.last_system_prompt.lower()
    assert "nunca" in llm.last_system_prompt.lower() or "solo" in llm.last_system_prompt.lower()


@pytest.mark.asyncio
async def test_tutor_system_prompt_forbids_markdown(seeded_db_path: str) -> None:
    """Reportado por el usuario: el tutor a veces devuelve **negrita** con
    asteriscos — se ve mal en el chat Y el TTS lee "asterisk" en voz alta.
    Es una conversación hablada, no texto con formato."""
    llm = _CapturingLLM()
    with db_connection(seeded_db_path) as conn:
        await get_tutor_reply(
            conn, llm,
            text="hello", history=[], session_id=None, topic="", wpm=0.0, fillers=0,
        )

    assert "markdown" in llm.last_system_prompt.lower()


@pytest.mark.asyncio
async def test_tutor_system_prompt_includes_todays_word_forms(seeded_db_path: str) -> None:
    llm = _CapturingLLM()
    with db_connection(seeded_db_path) as conn:
        plan = build_todays_plan(conn)
        await get_tutor_reply(
            conn, llm,
            text="hello", history=[], session_id=None, topic="", wpm=0.0, fillers=0,
        )

    first_word = plan["week_words"][0]["form"]
    assert first_word in llm.last_system_prompt


@pytest.mark.asyncio
async def test_tutor_system_prompt_mentions_stress_errors(seeded_db_path: str) -> None:
    """ITER-2: integración de stress_results al tutor — si el alumno
    acentuó mal una palabra en conversación libre, el tutor lo sabe y
    puede mencionarlo con calidez, sin forzarlo cada turno."""
    llm = _CapturingLLM()
    with db_connection(seeded_db_path) as conn:
        await get_tutor_reply(
            conn, llm,
            text="I like banana", history=[], session_id=None, topic="", wpm=0.0, fillers=0,
            stress_results=[
                {"word": "banana", "expected_syl": 1, "detected_syl": 0, "correct": False}
            ],
        )

    assert "banana" in llm.last_system_prompt


@pytest.mark.asyncio
async def test_tutor_system_prompt_omits_stress_note_when_all_correct(
    seeded_db_path: str,
) -> None:
    llm = _CapturingLLM()
    with db_connection(seeded_db_path) as conn:
        await get_tutor_reply(
            conn, llm,
            text="I like banana", history=[], session_id=None, topic="", wpm=0.0, fillers=0,
            stress_results=[
                {"word": "banana", "expected_syl": 1, "detected_syl": 1, "correct": True}
            ],
        )

    assert "banana" not in llm.last_system_prompt
