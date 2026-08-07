import pytest

from backend import seed
from backend.database import db_connection
from backend.providers.base import LLMProvider
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
async def test_tutor_system_prompt_includes_explicit_chunk_today(seeded_db_path: str) -> None:
    """El chunk tiene que ser el que el frontend YA mostró en módulo 2 (lo
    manda explícito), no uno recalculado en el backend — antes se llamaba
    a build_todays_plan(conn) de nuevo en cada turno de módulo 3, que podía
    devolver un chunk distinto si la rotación cambió entre medio (más
    probable ahora que la rotación de módulo 2 funciona de verdad).
    Reportado por el usuario: "no hay conexión entre módulos"."""
    llm = _CapturingLLM()
    with db_connection(seeded_db_path) as conn:
        await get_tutor_reply(
            conn, llm,
            text="hello", history=[], session_id=None, topic="", wpm=0.0, fillers=0,
            chunk_today="Be careful with that.",
        )

    assert "Be careful with that." in llm.last_system_prompt


@pytest.mark.asyncio
async def test_tutor_system_prompt_does_not_recompute_chunk_from_db(
    seeded_db_path: str,
) -> None:
    """Sin chunk_today explícito, el prompt no debe inventar uno leyendo
    la DB de nuevo — la fuente de verdad es lo que el frontend ya mostró
    en pantalla, no un recálculo que puede haber rotado."""
    llm = _CapturingLLM()
    with db_connection(seeded_db_path) as conn:
        db_chunk = conn.execute("SELECT chunk FROM chunks LIMIT 1").fetchone()["chunk"]
        await get_tutor_reply(
            conn, llm,
            text="hello", history=[], session_id=None, topic="", wpm=0.0, fillers=0,
        )

    assert db_chunk not in llm.last_system_prompt


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
async def test_tutor_system_prompt_includes_explicit_week_words(seeded_db_path: str) -> None:
    llm = _CapturingLLM()
    with db_connection(seeded_db_path) as conn:
        await get_tutor_reply(
            conn, llm,
            text="hello", history=[], session_id=None, topic="", wpm=0.0, fillers=0,
            week_words=["thought", "went"],
        )

    assert "thought" in llm.last_system_prompt
    assert "went" in llm.last_system_prompt


@pytest.mark.asyncio
async def test_tutor_system_prompt_includes_pattern_words_from_module_1(
    seeded_db_path: str,
) -> None:
    """Reportado por el usuario: "módulo 3 debe usar como insumos las
    palabras revisadas en módulo 1 y 2 — de momento no hay conexión entre
    módulos". Las palabras del patrón de pronunciación (módulo 1) nunca se
    le mencionaban al tutor — gap total, no solo un problema de datos
    obsoletos como el del chunk."""
    llm = _CapturingLLM()
    with db_connection(seeded_db_path) as conn:
        await get_tutor_reply(
            conn, llm,
            text="hello", history=[], session_id=None, topic="", wpm=0.0, fillers=0,
            pattern_words=["average", "manage", "village"],
        )

    assert "average" in llm.last_system_prompt
    assert "manage" in llm.last_system_prompt
    assert "módulo 1" in llm.last_system_prompt.lower()


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


@pytest.mark.asyncio
async def test_tutor_persists_comprehensibility_estimate(seeded_db_path: str) -> None:
    """Reportado por el usuario (investigación de "siempre me salen los
    mismos ejercicios"): sessions.comprehensibility nunca se escribía en
    ningún lado del código, así que _difficulty() se quedaba congelada en
    "maintain" para siempre. get_tutor_reply ahora la estima (services/
    comprehension.py, heurística sin costo extra de LLM) y la persiste."""
    llm = _CapturingLLM()
    with db_connection(seeded_db_path) as conn:
        _, session_id = await get_tutor_reply(
            conn, llm,
            text="I go to work every day and I like it a lot",
            history=[], session_id=None, topic="", wpm=120.0, fillers=0,
        )

        row = conn.execute(
            "SELECT comprehensibility FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()

    assert row["comprehensibility"] == pytest.approx(5.0)


@pytest.mark.asyncio
async def test_tutor_leaves_comprehensibility_null_for_empty_text(seeded_db_path: str) -> None:
    llm = _CapturingLLM()
    with db_connection(seeded_db_path) as conn:
        _, session_id = await get_tutor_reply(
            conn, llm, text="", history=[], session_id=None, topic="", wpm=0.0, fillers=0,
        )

        row = conn.execute(
            "SELECT comprehensibility FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()

    assert row["comprehensibility"] is None
