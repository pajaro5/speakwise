import re
import sqlite3
from datetime import date

from backend.database import (
    log_phoneme_errors,
    log_stress_results,
    mark_chunk_spontaneous,
    mark_chunk_used,
    upsert_pattern_progress,
    upsert_user_progress,
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


def log_chunk_spontaneous_use(
    conn: sqlite3.Connection, *, session_id: int, chunk: str, transcript: str
) -> bool:
    """Detecta si el chunk del día aparece SIN que se le pidiera al alumno
    (conversación libre, módulo 3) — a diferencia de log_chunk_used
    (práctica forzada, módulo 2), no pisa chunk_used/chunk_produced, marca
    una columna separada. DESIGN.md define esta señal para elegir el chunk
    del día ("menos usado espontáneamente"), pero nunca se había construido
    la detección — chunk_spontaneous se quedaba siempre en 0, y módulo 2
    repetía indefinidamente el chunk de menor rango (bug real reportado
    por el usuario)."""
    chunk_core = re.sub(r"[.!?]+$", "", chunk.strip()).lower()
    spontaneous = chunk_core in transcript.strip().lower()
    if spontaneous:
        mark_chunk_spontaneous(conn, session_id)
    return spontaneous


def log_words_used(
    conn: sqlite3.Connection, *, transcript: str, week_words: list[dict]
) -> list[str]:
    """Marca en user_progress (repaso espaciado) cualquier week_word que
    aparezca en la transcripción de conversación libre (módulo 3) — solo
    evidencia positiva real, nunca penaliza ausencia (ver
    upsert_user_progress). Antes de esto, user_progress nunca se escribía
    en ningún lado, así que las week_words nunca cambiaban (bug real
    reportado por el usuario, mismo patrón que el chunk de módulo 2).
    `today` se calcula acá, no lo manda el cliente (mismo criterio que
    upsert_pattern_progress: nunca confiar en el reloj del navegador)."""
    today = date.today().isoformat()
    transcript_tokens = {
        w.strip(".,!?¿¡").lower() for w in transcript.split()
    }
    used = []
    for w in week_words:
        if w["form"].lower() in transcript_tokens:
            upsert_user_progress(conn, w["form_id"], context="conv_prod", today=today)
            used.append(w["form"])
    return used


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
    week_words: list[dict] | None = None,
) -> dict:
    if event == "words_used":
        if transcript is None:
            raise InvalidLogEventError("transcript es requerido para event=words_used")
        used = log_words_used(conn, transcript=transcript, week_words=week_words or [])
        return {"ok": True, "words_used": used}

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

    if event == "chunk_spontaneous":
        if chunk is None or transcript is None:
            raise InvalidLogEventError(
                "chunk y transcript son requeridos para event=chunk_spontaneous"
            )
        spontaneous = log_chunk_spontaneous_use(
            conn, session_id=session_id, chunk=chunk, transcript=transcript
        )
        return {"ok": True, "spontaneous": spontaneous}

    if chunk is None or transcript is None:
        raise InvalidLogEventError("chunk y transcript son requeridos para event=chunk_used")
    produced = log_chunk_used(conn, session_id=session_id, chunk=chunk, transcript=transcript)
    return {"ok": True, "produced": produced}
