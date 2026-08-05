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


def test_log_pattern_practiced_updates_accuracy_from_stress_results(db_path: str) -> None:
    """ITER-2: si se pasan stress_results (del análisis acústico de
    /api/transcribe), pattern_progress.accuracy refleja el resultado real
    en vez de quedar en 0.0 para siempre."""
    with db_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO phonetic_patterns (id, name, priority) VALUES (1, '-age/-idge', 1)"
        )
        conn.commit()

        log_pattern_practiced(
            conn,
            pattern_id=1,
            stress_results=[
                {"word": "average", "expected_syl": 0, "detected_syl": 0, "correct": True},
                {"word": "manage", "expected_syl": 0, "detected_syl": 1, "correct": False},
            ],
        )

        row = conn.execute(
            "SELECT accuracy FROM pattern_progress WHERE pattern_id = 1"
        ).fetchone()

    assert row["accuracy"] == pytest.approx(0.5)


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


def test_log_chunk_used_ignores_trailing_punctuation_mismatch(db_path: str) -> None:
    """Reportado por el usuario: dijo "Be careful with that" correctamente
    pero no lo detectó — el chunk en la DB tiene punto final ("Be careful
    with that.") y el transcript de Whisper no, así que el match exacto
    por substring fallaba. Mismo bug que ya se corrigió en el resaltado
    del frontend (Fase 9.5), ahora en la detección real."""
    from backend.database import create_session

    with db_connection(db_path) as conn:
        session_id = create_session(
            conn, date="2026-08-05", topic="", transcript="", wpm=0.0, fillers=0, feedback="",
        )

        produced = log_chunk_used(
            conn,
            session_id=session_id,
            chunk="Be careful with that.",
            transcript="Be careful with that",
        )

    assert produced is True


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
