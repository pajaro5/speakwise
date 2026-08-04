import sqlite3

from backend.database import mark_chunk_used, upsert_pattern_progress
from backend.services.exceptions import InvalidLogEventError


def log_pattern_practiced(conn: sqlite3.Connection, *, pattern_id: int) -> None:
    upsert_pattern_progress(conn, pattern_id=pattern_id)


def log_chunk_used(
    conn: sqlite3.Connection, *, session_id: int, chunk: str, transcript: str
) -> bool:
    """Marca si el chunk aparece en la transcripción (case-insensitive).

    Verificación simple por substring, no fuzzy matching — suficiente para
    detectar si el alumno repitió el chunk casi textual cuando se lo pide
    el módulo de práctica forzada.
    """
    produced = chunk.strip().lower() in transcript.strip().lower()
    mark_chunk_used(conn, session_id, chunk=chunk, produced=produced)
    return produced


def handle_log_event(
    conn: sqlite3.Connection,
    *,
    session_id: int,
    event: str,
    pattern_id: int | None,
    chunk: str | None,
    transcript: str | None,
) -> dict:
    if event == "pattern_practiced":
        if pattern_id is None:
            raise InvalidLogEventError("pattern_id es requerido para event=pattern_practiced")
        log_pattern_practiced(conn, pattern_id=pattern_id)
        return {"ok": True}

    if chunk is None or transcript is None:
        raise InvalidLogEventError("chunk y transcript son requeridos para event=chunk_used")
    produced = log_chunk_used(conn, session_id=session_id, chunk=chunk, transcript=transcript)
    return {"ok": True, "produced": produced}
