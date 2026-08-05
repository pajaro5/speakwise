import sqlite3

import pytest

from backend.database import db_connection

EXPECTED_TABLES = {
    "words", "word_forms", "word_properties", "chunks", "phonetic_patterns",
    "curriculum_plan", "sessions", "user_progress", "pattern_progress", "phoneme_log",
}


@pytest.fixture
def temp_db_path(tmp_path) -> str:
    return str(tmp_path / "test.db")


def test_schema_creates_all_tables(temp_db_path: str) -> None:
    with db_connection(temp_db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        table_names = {row["name"] for row in rows}

    assert EXPECTED_TABLES.issubset(table_names)


def test_foreign_keys_pragma_is_on(temp_db_path: str) -> None:
    with db_connection(temp_db_path) as conn:
        result = conn.execute("PRAGMA foreign_keys").fetchone()[0]

    assert result == 1


def test_journal_mode_is_wal(temp_db_path: str) -> None:
    with db_connection(temp_db_path) as conn:
        result = conn.execute("PRAGMA journal_mode").fetchone()[0]

    assert result == "wal"


def test_schema_is_idempotent(temp_db_path: str) -> None:
    with db_connection(temp_db_path):
        pass
    with db_connection(temp_db_path) as conn:
        conn.execute("INSERT INTO words (lemma, rank, type) VALUES ('think', 1, 'irregular_verb')")
        conn.commit()

    with db_connection(temp_db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]

    assert count == 1


def test_row_factory_allows_dict_style_access(temp_db_path: str) -> None:
    with db_connection(temp_db_path) as conn:
        conn.execute("INSERT INTO words (lemma, rank, type) VALUES ('go', 2, 'irregular_verb')")
        conn.commit()
        row = conn.execute("SELECT * FROM words WHERE lemma = 'go'").fetchone()

    assert row["lemma"] == "go"
    assert row["rank"] == 2


def test_connection_closes_after_context_manager(temp_db_path: str) -> None:
    with db_connection(temp_db_path) as conn:
        pass

    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")


def test_upsert_pattern_progress_creates_row_on_first_practice(temp_db_path: str) -> None:
    from backend.database import upsert_pattern_progress

    with db_connection(temp_db_path) as conn:
        conn.execute(
            "INSERT INTO phonetic_patterns (id, name, priority) VALUES (1, '-age/-idge', 1)"
        )
        conn.commit()

        upsert_pattern_progress(conn, pattern_id=1)

        row = conn.execute(
            "SELECT * FROM pattern_progress WHERE pattern_id = 1"
        ).fetchone()

    assert row["stage"] == 1
    assert row["sessions_practiced"] == 1
    assert row["last_seen"] is not None


def test_upsert_pattern_progress_increments_on_repeat(temp_db_path: str) -> None:
    from backend.database import upsert_pattern_progress

    with db_connection(temp_db_path) as conn:
        conn.execute(
            "INSERT INTO phonetic_patterns (id, name, priority) VALUES (1, '-age/-idge', 1)"
        )
        conn.commit()

        upsert_pattern_progress(conn, pattern_id=1)
        upsert_pattern_progress(conn, pattern_id=1)

        row = conn.execute(
            "SELECT * FROM pattern_progress WHERE pattern_id = 1"
        ).fetchone()

    assert row["sessions_practiced"] == 2


def test_upsert_pattern_progress_updates_accuracy_from_stress_results(
    temp_db_path: str,
) -> None:
    """ITER-2: antes de tener análisis acústico, accuracy quedaba en 0.0
    para siempre — ahora se actualiza con el resultado real de sílaba
    tónica del intento de práctica (correct/total palabras analizadas)."""
    from backend.database import upsert_pattern_progress

    with db_connection(temp_db_path) as conn:
        conn.execute(
            "INSERT INTO phonetic_patterns (id, name, priority) VALUES (1, '-age/-idge', 1)"
        )
        conn.commit()

        upsert_pattern_progress(conn, pattern_id=1, correct=1, total=2)
        row = conn.execute(
            "SELECT accuracy FROM pattern_progress WHERE pattern_id = 1"
        ).fetchone()
        assert row["accuracy"] == pytest.approx(0.5)

        upsert_pattern_progress(conn, pattern_id=1, correct=2, total=2)
        row = conn.execute(
            "SELECT accuracy FROM pattern_progress WHERE pattern_id = 1"
        ).fetchone()
        assert row["accuracy"] == pytest.approx(0.75)


def test_upsert_pattern_progress_without_stress_results_keeps_accuracy_at_zero(
    temp_db_path: str,
) -> None:
    from backend.database import upsert_pattern_progress

    with db_connection(temp_db_path) as conn:
        conn.execute(
            "INSERT INTO phonetic_patterns (id, name, priority) VALUES (1, '-age/-idge', 1)"
        )
        conn.commit()

        upsert_pattern_progress(conn, pattern_id=1)

        row = conn.execute(
            "SELECT accuracy FROM pattern_progress WHERE pattern_id = 1"
        ).fetchone()
    assert row["accuracy"] == 0.0


def test_log_stress_results_records_only_errors(temp_db_path: str) -> None:
    """DoD de BACKLOG.md: "después de una sesión, SELECT * FROM phoneme_log
    WHERE session_id = ? muestra errores reales" — solo se loguean los
    intentos incorrectos, los correctos no son "errores"."""
    from backend.database import create_session, log_stress_results

    with db_connection(temp_db_path) as conn:
        session_id = create_session(
            conn, date="2026-08-05", topic="", transcript="", wpm=0.0, fillers=0, feedback="",
        )

        log_stress_results(
            conn,
            session_id,
            [
                {"word": "average", "expected_syl": 0, "detected_syl": 0, "correct": True},
                {"word": "manage", "expected_syl": 0, "detected_syl": 1, "correct": False},
            ],
        )

        rows = conn.execute(
            "SELECT * FROM phoneme_log WHERE session_id = ?", (session_id,)
        ).fetchall()

    assert len(rows) == 1
    assert rows[0]["word"] == "manage"
    assert rows[0]["correct"] == 0


def test_mark_chunk_used_updates_session_row(temp_db_path: str) -> None:
    from backend.database import create_session, mark_chunk_used

    with db_connection(temp_db_path) as conn:
        session_id = create_session(
            conn, date="2026-08-05", topic="", transcript="hi", wpm=0.0, fillers=0, feedback="",
        )

        mark_chunk_used(conn, session_id, chunk="I was thinking maybe", produced=True)

        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()

    assert row["chunk_used"] == "I was thinking maybe"
    assert row["chunk_produced"] == 1
