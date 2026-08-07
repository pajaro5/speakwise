import sqlite3
from datetime import date

from backend.database import create_session, update_session
from backend.providers.base import LLMProvider
from backend.services.comprehension import estimate_comprehensibility
from backend.services.curriculum import build_todays_plan

BASE_SYSTEM_PROMPT = (
    "Sos un tutor de inglés conversacional. El objetivo del alumno es la "
    "inteligibilidad, no sonar nativo. Corregí con calidez, en inglés simple, "
    "y siempre proponé la forma correcta cuando el alumno comete un error. "
    "IMPORTANTE: respondé siempre en inglés, nunca en español — el alumno "
    "está practicando inglés y necesita escuchar/leer solo inglés en tus "
    "respuestas, incluso para las correcciones. IMPORTANTE: nunca uses "
    "markdown (nada de **negrita**, *cursiva*, `código`, títulos con #, "
    "listas con -) — tu respuesta se muestra como texto plano en un chat Y "
    "se lee en voz alta con text-to-speech, así que el markdown se ve como "
    "asteriscos literales y el TTS los lee en voz alta."
)


def _build_system_prompt(
    conn: sqlite3.Connection, stress_results: list[dict] | None = None
) -> str:
    plan = build_todays_plan(conn)
    parts = [BASE_SYSTEM_PROMPT]

    chunk = plan.get("chunk_today")
    if chunk:
        parts.append(
            f'Chunk del día para practicar: "{chunk["chunk"]}". Si surge naturalmente '
            "en la charla, invitá al alumno a usarlo — sin forzarlo."
        )

    words = plan.get("week_words") or []
    if words:
        forms = ", ".join(w["form"] for w in words)
        parts.append(
            f"Palabras a reforzar hoy: {forms}. Si podés, guiá la conversación para "
            "que aparezcan de forma natural."
        )

    incorrect = [r["word"] for r in (stress_results or []) if not r["correct"]]
    if incorrect:
        mispronounced = ", ".join(incorrect)
        parts.append(
            f"Justo ahora el alumno acentuó mal la sílaba tónica en: {mispronounced}. "
            "Si tiene sentido en el flujo de la charla, mencionalo con calidez y "
            "mostrale brevemente cómo suena bien — sin interrumpir la conversación "
            "ni retar por eso cada turno."
        )

    return " ".join(parts)


async def get_tutor_reply(
    conn: sqlite3.Connection,
    llm: LLMProvider,
    *,
    text: str,
    history: list[dict],
    session_id: int | None,
    topic: str,
    wpm: float,
    fillers: int,
    stress_results: list[dict] | None = None,
) -> tuple[str, int]:
    messages = [*history, {"role": "user", "content": text}]
    system_prompt = _build_system_prompt(conn, stress_results)
    reply = await llm.complete(messages=messages, system=system_prompt)
    comprehensibility = estimate_comprehensibility(
        wpm=wpm, fillers=fillers, word_count=len(text.split())
    )

    if session_id is None:
        session_id = create_session(
            conn,
            date=date.today().isoformat(),
            topic=topic,
            transcript=text,
            wpm=wpm,
            fillers=fillers,
            feedback=reply,
            comprehensibility=comprehensibility,
        )
    else:
        update_session(
            conn, session_id, transcript=text, wpm=wpm, fillers=fillers, feedback=reply,
            comprehensibility=comprehensibility,
        )

    return reply, session_id
