import pytest

from backend.database import db_connection
from backend.services.log import log_chunk_used, log_pattern_practiced


@pytest.fixture
def db_path(tmp_path) -> str:
    return str(tmp_path / "log_test.db")


def test_log_pattern_practiced_creates_progress_row(db_path: str) -> None:
    with db_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO phonetic_patterns (id, name, priority) VALUES (1, '-age/-idge', 1)"
        )
        conn.commit()

        log_pattern_practiced(conn, pattern_id=1)

        row = conn.execute(
            "SELECT sessions_practiced FROM pattern_progress WHERE pattern_id = 1"
        ).fetchone()

    assert row["sessions_practiced"] == 1


def test_log_chunk_used_marks_produced_when_chunk_in_transcript(db_path: str) -> None:
    from backend.database import create_session

    with db_connection(db_path) as conn:
        session_id = create_session(
            conn, date="2026-08-05", topic="", transcript="", wpm=0.0, fillers=0, feedback="",
        )

        log_chunk_used(
            conn,
            session_id=session_id,
            chunk="I was thinking maybe",
            transcript="Well, I was thinking maybe we could go tomorrow",
        )

        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()

    assert row["chunk_produced"] == 1


def test_log_chunk_used_marks_not_produced_when_chunk_absent(db_path: str) -> None:
    from backend.database import create_session

    with db_connection(db_path) as conn:
        session_id = create_session(
            conn, date="2026-08-05", topic="", transcript="", wpm=0.0, fillers=0, feedback="",
        )

        log_chunk_used(
            conn,
            session_id=session_id,
            chunk="I was thinking maybe",
            transcript="I like pizza",
        )

        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()

    assert row["chunk_produced"] == 0
