import json
import re
import sqlite3

from backend.database import upsert_pattern_progress

_MARKUP_RE = re.compile(r"[~*]")


def _strip_markup(word: str) -> str:
    return _MARKUP_RE.sub("", word)


def build_diagnostic_plan(conn: sqlite3.Connection) -> list[dict]:
    """Palabras de los patrones priority=1 (mayor impacto real para un
    hispanohablante, ver Fase A del plan de mejora) para leer en un solo
    diagnóstico inicial — evita que la rotación de módulo 1 arranque
    completamente en frío, como sí hacía antes (ELSA/BoldVoice arrancan
    con un diagnóstico similar)."""
    rows = conn.execute(
        "SELECT id, name, family FROM phonetic_patterns WHERE priority = 1"
    ).fetchall()
    return [
        {
            "pattern_id": row["id"],
            "name": row["name"],
            "words": [_strip_markup(w) for w in json.loads(row["family"])],
        }
        for row in rows
    ]


def apply_diagnostic_results(
    conn: sqlite3.Connection,
    plan: list[dict],
    *,
    transcript_text: str,
    phoneme_errors: list[dict],
) -> None:
    """Para cada patrón del diagnóstico, cuenta cuántas de sus palabras
    aparecieron en la transcripción (evidencia de que se intentaron) y
    cuántas de esas están en phoneme_errors — siembra pattern_progress
    con un accuracy inicial real. Si ninguna palabra del patrón aparece
    (el alumno no llegó a decirla), no se toca ese patrón — mismo
    criterio que pattern_progress/user_progress: sin evidencia real, no
    se inventa un resultado."""
    error_words = {e["word"].lower() for e in phoneme_errors}
    transcript_tokens = {w.strip(".,!?¿¡").lower() for w in transcript_text.split()}

    for pattern in plan:
        words = [w.lower() for w in pattern["words"] if " " not in w]
        attempted = [w for w in words if w in transcript_tokens]
        if not attempted:
            continue
        correct = sum(1 for w in attempted if w not in error_words)
        upsert_pattern_progress(
            conn, pattern_id=pattern["pattern_id"], correct=correct, total=len(attempted)
        )
