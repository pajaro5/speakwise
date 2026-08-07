import sqlite3

import pytest

from backend import seed
from backend.database import db_connection, upsert_pattern_progress
from backend.services.curriculum import (
    _chunk_of_the_day,
    _difficulty,
    _forms_to_review,
    _pattern_of_the_day,
    build_todays_plan,
)


@pytest.fixture
def seeded_db_path(tmp_path) -> str:
    db_path = str(tmp_path / "curriculum_test.db")
    seed.run(db_path)
    return db_path


def _form_id(conn: sqlite3.Connection, lemma: str, tense: str) -> int:
    row = conn.execute(
        "SELECT wf.id FROM word_forms wf JOIN words w ON w.id = wf.word_id "
        "WHERE w.lemma = ? AND wf.tense = ?",
        (lemma, tense),
    ).fetchone()
    return row["id"]


def test_forms_to_review_cold_start_returns_up_to_limit(seeded_db_path: str) -> None:
    with db_connection(seeded_db_path) as conn:
        forms = _forms_to_review(conn, today="2026-08-04", limit=5)

    assert len(forms) == 5
    for f in forms:
        assert set(f.keys()) == {"form_id", "form", "tense", "lfc_focus", "score"}
        assert f["score"] == 0.0  # nada revisado todavia
        assert isinstance(f["form_id"], int)


def test_forms_to_review_excludes_not_yet_due_and_orders_by_score(
    seeded_db_path: str,
) -> None:
    with db_connection(seeded_db_path) as conn:
        due_id = _form_id(conn, "think", "past")  # "thought"
        not_due_id = _form_id(conn, "go", "past")  # "went"
        conn.execute(
            "INSERT INTO user_progress (form_id, context, score, next_review) "
            "VALUES (?, 'conv_prod', 0.1, '2026-08-01')",
            (due_id,),
        )
        conn.execute(
            "INSERT INTO user_progress (form_id, context, score, next_review) "
            "VALUES (?, 'conv_prod', 0.9, '2099-01-01')",
            (not_due_id,),
        )
        conn.commit()

        # limit alto: con corpus mayormente sin tocar (score 0.0 por default),
        # "thought" (score 0.1) queda detras de esos empates - necesitamos ver
        # TODAS las filas no excluidas para verificar la exclusion, no el orden.
        forms = _forms_to_review(conn, today="2026-08-04", limit=300)

    returned = {f["form"] for f in forms}
    assert "thought" in returned
    assert "went" not in returned


def test_pattern_of_the_day_cold_start_picks_priority_1(seeded_db_path: str) -> None:
    with db_connection(seeded_db_path) as conn:
        pattern = _pattern_of_the_day(conn)

    assert pattern is not None
    assert set(pattern.keys()) == {
        "id", "name", "rule_es", "rule_ipa", "family", "family_stress", "family_respelling",
    }
    assert isinstance(pattern["family"], list)
    assert isinstance(pattern["id"], int)


def test_pattern_of_the_day_includes_stress_caps_and_respelling(seeded_db_path: str) -> None:
    """El usuario pidió mostrar la sílaba tónica en mayúsculas (ej. "aVERage")
    y, junto al IPA, una guía de pronunciación simple sin símbolos (ej.
    "buk" para "book"). family_stress viene curado a mano en patterns.csv
    (igual que el markup ~x~/*x*); family_respelling se calcula on the fly
    con simple_respelling() (fonema-based, no depende de la ortografía)."""
    with db_connection(seeded_db_path) as conn:
        pattern = _pattern_of_the_day(conn)

    assert isinstance(pattern["family_stress"], list)
    assert len(pattern["family_stress"]) == len(pattern["family"])
    assert isinstance(pattern["family_respelling"], list)
    assert len(pattern["family_respelling"]) == len(pattern["family"])
    # el patrón de prioridad 1 en cold-start es -age/-idge (ver test de arriba)
    assert "AVerage" in pattern["family_stress"]
    assert "A-ver-ij" in pattern["family_respelling"]


def test_pattern_of_the_day_prefers_least_practiced(seeded_db_path: str) -> None:
    """Reportado por el usuario: "en todas las pruebas siempre iniciamos con
    lo mismo, age idge, eso es correcto?" — no lo era del todo: sin scoring
    real de precisión (eso es ITER-2), el mismo patrón de prioridad 1 se
    repetía siempre porque sessions_practiced no influía en el orden."""
    with db_connection(seeded_db_path) as conn:
        first_pick = _pattern_of_the_day(conn)
        for _ in range(3):
            upsert_pattern_progress(conn, pattern_id=first_pick["id"])

        second_pick = _pattern_of_the_day(conn)

    assert second_pick["id"] != first_pick["id"]


def test_pattern_of_the_day_excludes_mastered_stage_4(seeded_db_path: str) -> None:
    with db_connection(seeded_db_path) as conn:
        row = conn.execute(
            "SELECT id, name FROM phonetic_patterns WHERE priority = 1 LIMIT 1"
        ).fetchone()
        mastered_id, mastered_name = row["id"], row["name"]
        conn.execute(
            "INSERT INTO pattern_progress (pattern_id, stage, accuracy) VALUES (?, 4, 0.95)",
            (mastered_id,),
        )
        conn.commit()

        pattern = _pattern_of_the_day(conn)

    assert pattern["name"] != mastered_name


def test_chunk_of_the_day_returns_a_chunk(seeded_db_path: str) -> None:
    with db_connection(seeded_db_path) as conn:
        chunk = _chunk_of_the_day(conn)

    assert chunk is not None
    assert set(chunk.keys()) == {
        "chunk", "function", "meaning_es", "spontaneous_uses", "produced_uses",
    }
    assert chunk["spontaneous_uses"] == 0
    assert chunk["produced_uses"] == 0
    assert chunk["meaning_es"]


def test_chunk_of_the_day_prefers_least_spontaneous_uses(seeded_db_path: str) -> None:
    with db_connection(seeded_db_path) as conn:
        chunk_text = conn.execute("SELECT chunk FROM chunks LIMIT 1").fetchone()["chunk"]
        for i in range(3):
            conn.execute(
                "INSERT INTO sessions (date, chunk_used, chunk_spontaneous) "
                "VALUES (?, ?, 1)",
                (f"2026-08-0{i+1}", chunk_text),
            )
        conn.commit()

        chunk = _chunk_of_the_day(conn)

    assert chunk["chunk"] != chunk_text


def test_chunk_of_the_day_prefers_least_produced_uses(seeded_db_path: str) -> None:
    """Reportado por el usuario: módulo 2 siempre repite "Be careful with
    that." — causa real: chunk_spontaneous nunca se escribe en ningún lado
    del código (la detección de uso espontáneo en módulo 3 no existía),
    así que siempre vale 0 para todos los chunks y el desempate cae en el
    rango de la palabra, que nunca cambia. produced_uses sí se registra de
    verdad cada vez que se completa módulo 2 (mark_chunk_used) — usarlo
    como segundo criterio de desempate hace que la rotación funcione ya
    mismo, sin esperar a que se use espontáneamente en conversación libre."""
    with db_connection(seeded_db_path) as conn:
        chunk_text = conn.execute("SELECT chunk FROM chunks LIMIT 1").fetchone()["chunk"]
        for i in range(3):
            conn.execute(
                "INSERT INTO sessions (date, chunk_used, chunk_produced) "
                "VALUES (?, ?, 1)",
                (f"2026-08-0{i+1}", chunk_text),
            )
        conn.commit()

        chunk = _chunk_of_the_day(conn)

    assert chunk["chunk"] != chunk_text


def test_difficulty_maintain_when_no_sessions(seeded_db_path: str) -> None:
    with db_connection(seeded_db_path) as conn:
        assert _difficulty(conn) == "maintain"


def test_difficulty_increase_when_avg_comprehensibility_high(seeded_db_path: str) -> None:
    with db_connection(seeded_db_path) as conn:
        for i in range(5):
            conn.execute(
                "INSERT INTO sessions (date, comprehensibility) VALUES (?, 4.5)",
                (f"2026-08-0{i+1}",),
            )
        conn.commit()

        assert _difficulty(conn) == "increase"


def test_difficulty_decrease_when_avg_comprehensibility_low(seeded_db_path: str) -> None:
    with db_connection(seeded_db_path) as conn:
        for i in range(5):
            conn.execute(
                "INSERT INTO sessions (date, comprehensibility) VALUES (?, 2.0)",
                (f"2026-08-0{i+1}",),
            )
        conn.commit()

        assert _difficulty(conn) == "decrease"


def test_build_todays_plan_has_full_contract_shape(seeded_db_path: str) -> None:
    with db_connection(seeded_db_path) as conn:
        plan = build_todays_plan(conn, today="2026-08-04")

    assert set(plan.keys()) == {
        "week_words", "pattern_focus", "chunk_today", "difficulty", "topic_options",
        "conversation_starters", "linking_words",
    }
    assert len(plan["topic_options"]) == 3
    assert len(plan["conversation_starters"]) == 3
    assert len(plan["linking_words"]) == 3
    assert plan["difficulty"] == "maintain"


def test_build_todays_plan_corpus_content_under_300_tokens(seeded_db_path: str) -> None:
    import json

    with db_connection(seeded_db_path) as conn:
        plan = build_todays_plan(conn, today="2026-08-04")

    corpus_content = json.dumps(
        {
            "week_words": plan["week_words"],
            "pattern_focus": plan["pattern_focus"],
            "chunk_today": plan["chunk_today"],
        }
    )
    assert len(corpus_content) // 4 <= 300  # aproximacion de tokens, ver curriculum.py
