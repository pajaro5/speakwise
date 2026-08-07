import re
import sqlite3

from backend.database import (
    log_phoneme_errors,
    log_stress_results,
    mark_chunk_used,
    upsert_pattern_progress,
)
from backend.services.exceptions import InvalidLogEventError


def log_pattern_practiced(
    conn: sqlite3.Connection,
    *,
    pattern_id: int,
    session_id: int | None = None,
    stress_results: list[dict] | None = None,
    phoneme_errors: list[dict] | None = None,
    phoneme_evaluated: int | None = None,
) -> None:
    if stress_results:
        correct = sum(1 for r in stress_results if r["correct"])
        upsert_pattern_progress(
            conn, pattern_id=pattern_id, correct=correct, total=len(stress_results)
        )
        if session_id is not None:
            log_stress_results(conn, session_id, stress_results)
    elif phoneme_evaluated:
        # Fallback para patrones cuya familia es 100% monosílaba (ej.
        # "letras mudas kn-/wr-") — analyze_stress las ignora (no hay
        # contraste de sílaba tónica), así que stress_results siempre
        # queda vacío y su accuracy se quedaba congelada en 0.0 para
        # siempre, dominando la selección de "menos practicado" para
        # siempre (bug real reportado por el usuario).
        correct = phoneme_evaluated - len(phoneme_errors or [])
        upsert_pattern_progress(
            conn, pattern_id=pattern_id, correct=correct, total=phoneme_evaluated
        )
    else:
        upsert_pattern_progress(conn, pattern_id=pattern_id)

    if phoneme_errors and session_id is not None:
        log_phoneme_errors(conn, session_id, phoneme_errors)


def log_chunk_used(
    conn: sqlite3.Connection, *, session_id: int, chunk: str, transcript: str
) -> bool:
    """Marca si el chunk aparece en la transcripción (case-insensitive).

    Verificación simple por substring, no fuzzy matching — suficiente para
    detectar si el alumno repitió el chunk casi textual cuando se lo pide
    el módulo de práctica forzada.
    """
    chunk_core = re.sub(r"[.!?]+$", "", chunk.strip()).lower()
    produced = chunk_core in transcript.strip().lower()
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
    stress_results: list[dict] | None = None,
    phoneme_errors: list[dict] | None = None,
    phoneme_evaluated: int | None = None,
) -> dict:
    if event == "pattern_practiced":
        if pattern_id is None:
            raise InvalidLogEventError("pattern_id es requerido para event=pattern_practiced")
        log_pattern_practiced(
            conn,
            pattern_id=pattern_id,
            session_id=session_id,
            stress_results=stress_results,
            phoneme_errors=phoneme_errors,
            phoneme_evaluated=phoneme_evaluated,
        )
        return {"ok": True}

    if chunk is None or transcript is None:
        raise InvalidLogEventError("chunk y transcript son requeridos para event=chunk_used")
    produced = log_chunk_used(conn, session_id=session_id, chunk=chunk, transcript=transcript)
    return {"ok": True, "produced": produced}
