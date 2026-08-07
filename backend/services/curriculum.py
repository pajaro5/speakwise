import json
import random
import re
import sqlite3
from datetime import date

from backend.services.phoneme import simple_respelling

# ~x~/*x* -- mismo markup que parsea app.js (stripMarkup) para el TTS, usado
# acá para poder buscar la palabra "limpia" en cmudict.
_MARKUP_RE = re.compile(r"[~*]")


def _strip_markup(word: str) -> str:
    return _MARKUP_RE.sub("", word)

# Sin tabla de temas en el schema (DESIGN.md no la define) — pool curado en código.
TOPIC_POOL = [
    "tu semana de trabajo",
    "un viaje planeado",
    "algo que viste",
    "una película que te gustó",
    "un problema que resolviste",
    "planes para el fin de semana",
    "algo que aprendiste hace poco",
]

# Apoyo para conversación libre — reportado por el usuario ("me quedo en
# blanco"): frases para arrancar y conectores para enlazar ideas, además de
# los temas de TOPIC_POOL. Sin tabla propia en el schema, pool curado acá.
CONVERSATION_STARTERS = [
    "So, how's it going?",
    "What have you been up to lately?",
    "Guess what happened to me today.",
    "Have you ever tried something like this?",
    "What do you think about this?",
    "Can I tell you something?",
    "So, tell me about your day.",
    "I wanted to ask you something.",
]

LINKING_WORDS = [
    "for example",
    "also",
    "but",
    "however",
    "because",
    "on the other hand",
    "in addition",
    "between",
    "actually",
    "by the way",
]


def _forms_to_review(
    conn: sqlite3.Connection, today: str, limit: int = 5
) -> list[dict]:
    """Formas due para repaso, o formas nuevas si todavía no hay progreso (día 1).

    form_id (wf.id) se expone para que el frontend lo devuelva en /api/log
    (event=words_used) y así se pueda actualizar user_progress con la
    forma exacta que se usó en conversación libre."""
    rows = conn.execute(
        """
        SELECT wf.id AS form_id, wf.form, wf.tense, wf.lfc_focus,
               COALESCE(up.score, 0.0) AS score
        FROM word_forms wf
        JOIN words w ON w.id = wf.word_id
        LEFT JOIN user_progress up
            ON up.form_id = wf.id AND up.context = 'conv_prod'
        WHERE up.next_review IS NULL OR up.next_review <= :today
        ORDER BY COALESCE(up.score, 0.0) ASC, w.rank ASC
        LIMIT :limit
        """,
        {"today": today, "limit": limit},
    ).fetchall()
    return [dict(r) for r in rows]


def _pattern_of_the_day(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute(
        """
        SELECT p.id, p.name, p.rule_es, p.rule_ipa, p.family, p.family_stress
        FROM phonetic_patterns p
        LEFT JOIN pattern_progress pp ON pp.pattern_id = p.id
        WHERE pp.stage IS NULL OR pp.stage < 4
        ORDER BY COALESCE(pp.accuracy, 0.0) ASC,
                 COALESCE(pp.sessions_practiced, 0) ASC,
                 p.priority ASC
        LIMIT 1
        """
    ).fetchone()
    if row is None:
        return None
    family = json.loads(row["family"])
    return {
        "id": row["id"],
        "name": row["name"],
        "rule_es": row["rule_es"],
        "rule_ipa": row["rule_ipa"],
        "family": family,
        "family_stress": json.loads(row["family_stress"]),
        "family_respelling": [simple_respelling(_strip_markup(w)) for w in family],
    }


def _chunk_of_the_day(conn: sqlite3.Connection) -> dict | None:
    """spontaneous_uses (uso espontáneo en conversación libre, módulo 3) es
    la señal de repaso espaciado que pide DESIGN.md — pero produced_uses
    (práctica forzada en módulo 2, ya registrada por mark_chunk_used) es un
    desempate real disponible desde el primer día, mientras el alumno
    todavía no generó uso espontáneo. Sin esto, spontaneous_uses queda en
    0 para todos los chunks hasta que haya uso espontáneo real, y el
    desempate caía en el rango de la palabra (que nunca cambia) — bug real
    reportado por el usuario: módulo 2 siempre repetía "Be careful with
    that." (rank más bajo del corpus, "be")."""
    row = conn.execute(
        """
        SELECT c.chunk, c.function,
               COUNT(CASE WHEN s.chunk_spontaneous = 1 THEN 1 END) AS spontaneous_uses,
               COUNT(CASE WHEN s.chunk_produced = 1 THEN 1 END) AS produced_uses
        FROM chunks c
        JOIN words w ON w.id = c.word_id
        LEFT JOIN sessions s ON s.chunk_used = c.chunk
        WHERE w.rank <= 150
        GROUP BY c.id
        ORDER BY spontaneous_uses ASC, produced_uses ASC, w.rank ASC
        LIMIT 1
        """
    ).fetchone()
    if row is None:
        return None
    return {
        "chunk": row["chunk"],
        "function": row["function"],
        "spontaneous_uses": row["spontaneous_uses"],
        "produced_uses": row["produced_uses"],
    }


def _difficulty(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        """
        SELECT AVG(comprehensibility) AS avg_c FROM (
            SELECT comprehensibility FROM sessions ORDER BY date DESC LIMIT 5
        )
        """
    ).fetchone()
    avg_c = row["avg_c"]
    if avg_c is None:
        return "maintain"
    if avg_c > 4.0:
        return "increase"
    if avg_c < 3.0:
        return "decrease"
    return "maintain"


def build_todays_plan(conn: sqlite3.Connection, today: str | None = None) -> dict:
    """Plan pedagógico del día — DESIGN.md §5 GET /api/today, lógica en §7."""
    today = today or date.today().isoformat()
    return {
        "week_words": _forms_to_review(conn, today),
        "pattern_focus": _pattern_of_the_day(conn),
        "chunk_today": _chunk_of_the_day(conn),
        "difficulty": _difficulty(conn),
        "topic_options": random.sample(TOPIC_POOL, 3),
        "conversation_starters": random.sample(CONVERSATION_STARTERS, 3),
        "linking_words": random.sample(LINKING_WORDS, 3),
    }
