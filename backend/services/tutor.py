import sqlite3
from datetime import date

from backend.database import create_session, update_session
from backend.providers.base import LLMProvider

SYSTEM_PROMPT = (
    "Sos un tutor de inglés conversacional. El objetivo del alumno es la "
    "inteligibilidad, no sonar nativo. Corregí con calidez, en inglés simple, "
    "y siempre proponé la forma correcta cuando el alumno comete un error."
)


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
) -> tuple[str, int]:
    messages = [*history, {"role": "user", "content": text}]
    reply = await llm.complete(messages=messages, system=SYSTEM_PROMPT)

    if session_id is None:
        session_id = create_session(
            conn,
            date=date.today().isoformat(),
            topic=topic,
            transcript=text,
            wpm=wpm,
            fillers=fillers,
            feedback=reply,
        )
    else:
        update_session(
            conn, session_id, transcript=text, wpm=wpm, fillers=fillers, feedback=reply
        )

    return reply, session_id
