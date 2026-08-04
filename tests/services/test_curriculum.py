import sqlite3

import pytest

from backend import seed
from backend.database import db_connection
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
        assert set(f.keys()) == {"form", "tense", "lfc_focus", "score"}
        assert f["score"] == 0.0  # nada revisado todavia


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
    assert set(pattern.keys()) == {"name", "rule_es", "family"}
    assert isinstance(pattern["family"], list)


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
    assert set(chunk.keys()) == {"chunk", "function", "spontaneous_uses"}
    assert chunk["spontaneous_uses"] == 0


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
    }
    assert len(plan["topic_options"]) == 3
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
