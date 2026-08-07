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


def test_log_pattern_practiced_updates_accuracy_from_phoneme_evaluated_when_no_stress_results(
    db_path: str,
) -> None:
    """Reportado por el usuario: "cada vez que uso la app, me salen los
    mismos ejercicios". Causa real: el patrón "letras mudas kn-/wr-" tiene
    las 5 palabras monosílabas, y analyze_stress ignora monosílabas (no hay
    contraste de sílaba tónica) — stress_results siempre vacío, así que
    upsert_pattern_progress nunca recibía correct/total y accuracy se
    quedaba congelada en 0.0 para siempre, dominando la selección de "menos
    practicado" (_pattern_of_the_day ordena por accuracy ASC). Con
    phoneme_evaluated (cuenta independiente del número de sílabas) se
    puede calcular un accuracy real también para esos patrones."""
    with db_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO phonetic_patterns (id, name, priority) VALUES (1, 'letras mudas', 2)"
        )
        conn.commit()

        log_pattern_practiced(
            conn,
            pattern_id=1,
            phoneme_errors=[{"word": "write", "expected": "R AY1 T", "produced": "r eye"}],
            phoneme_evaluated=4,
        )

        row = conn.execute(
            "SELECT accuracy FROM pattern_progress WHERE pattern_id = 1"
        ).fetchone()

    assert row["accuracy"] == pytest.approx(0.75)


def test_log_pattern_practiced_keeps_accuracy_frozen_without_any_signal(db_path: str) -> None:
    """Sin stress_results NI phoneme_evaluated (ej. el usuario no dijo nada
    reconocible), no hay evidencia real de un intento — no se debe inventar
    un accuracy de 100% ni de 0%, se mantiene el comportamiento previo
    (congelado en 0.0, solo cuenta la exposición)."""
    with db_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO phonetic_patterns (id, name, priority) VALUES (1, 'letras mudas', 2)"
        )
        conn.commit()

        log_pattern_practiced(conn, pattern_id=1, phoneme_errors=[])

        row = conn.execute(
            "SELECT accuracy FROM pattern_progress WHERE pattern_id = 1"
        ).fetchone()

    assert row["accuracy"] == 0.0


def test_log_pattern_practiced_logs_phoneme_errors(db_path: str) -> None:
    """ITER-2: los phoneme_errors (comparación fonémica real, wav2vec2) se
    guardan en phoneme_log igual que los stress_results incorrectos."""
    from backend.database import create_session

    with db_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO phonetic_patterns (id, name, priority) VALUES (1, '-age/-idge', 1)"
        )
        session_id = create_session(
            conn, date="2026-08-05", topic="", transcript="", wpm=0.0, fillers=0, feedback="",
        )
        conn.commit()

        log_pattern_practiced(
            conn,
            pattern_id=1,
            session_id=session_id,
            phoneme_errors=[{"word": "banana", "expected": "AE1", "produced": "b ə n a n a"}],
        )

        rows = conn.execute(
            "SELECT * FROM phoneme_log WHERE session_id = ?", (session_id,)
        ).fetchall()

    assert len(rows) == 1
    assert rows[0]["word"] == "banana"


def test_log_chunk_spontaneous_marks_when_chunk_appears_unprompted(db_path: str) -> None:
    """Reportado por el usuario: módulo 2 siempre repite el mismo chunk —
    causa real: la detección de uso espontáneo en módulo 3 nunca se
    construyó (DESIGN.md la definía, pero el código para chequearla no
    existía). Este test cubre la pieza real: si el chunk del día aparece
    en la transcripción de conversación libre (módulo 3), se marca
    chunk_spontaneous=1 en la sesión."""
    from backend.database import create_session
    from backend.services.log import log_chunk_spontaneous_use

    with db_connection(db_path) as conn:
        session_id = create_session(
            conn, date="2026-08-07", topic="", transcript="", wpm=0.0, fillers=0, feedback="",
        )

        used = log_chunk_spontaneous_use(
            conn,
            session_id=session_id,
            chunk="Be careful with that.",
            transcript="Yeah, be careful with that, it's heavy.",
        )

        row = conn.execute("SELECT chunk_spontaneous FROM sessions WHERE id = ?", (session_id,)).fetchone()

    assert used is True
    assert row["chunk_spontaneous"] == 1


def test_log_chunk_spontaneous_does_not_mark_when_chunk_absent(db_path: str) -> None:
    from backend.database import create_session
    from backend.services.log import log_chunk_spontaneous_use

    with db_connection(db_path) as conn:
        session_id = create_session(
            conn, date="2026-08-07", topic="", transcript="", wpm=0.0, fillers=0, feedback="",
        )

        used = log_chunk_spontaneous_use(
            conn, session_id=session_id, chunk="Be careful with that.", transcript="I like pizza",
        )

        row = conn.execute("SELECT chunk_spontaneous FROM sessions WHERE id = ?", (session_id,)).fetchone()

    assert used is False
    assert row["chunk_spontaneous"] is None


def test_log_words_used_marks_matching_week_words(db_path: str) -> None:
    """Reportado por el usuario: "sigue repitiendo el chunk... seguro pasa
    lo mismo en módulo 3" — sí: user_progress nunca se escribía en ningún
    lado, así que las week_words de módulo 3 nunca cambiaban. Solo se
    marcan las formas que SÍ aparecieron (evidencia positiva) — no se
    penaliza la ausencia, el alumno puede simplemente no haber tenido
    ocasión de usar una palabra en esa charla en particular."""
    from backend.services.log import log_words_used

    with db_connection(db_path) as conn:
        word_id = conn.execute(
            "INSERT INTO words (lemma, rank, type) VALUES ('think', 1, 'verb')"
        ).lastrowid
        thought_id = conn.execute(
            "INSERT INTO word_forms (word_id, form, tense) VALUES (?, 'thought', 'past')",
            (word_id,),
        ).lastrowid
        went_id = conn.execute(
            "INSERT INTO word_forms (word_id, form, tense) VALUES (?, 'went', 'past')",
            (word_id,),
        ).lastrowid
        conn.commit()

        used = log_words_used(
            conn,
            transcript="I thought about it yesterday.",
            week_words=[
                {"form_id": thought_id, "form": "thought"},
                {"form_id": went_id, "form": "went"},
            ],
        )

        row = conn.execute(
            "SELECT COUNT(*) AS n FROM user_progress WHERE form_id = ?", (thought_id,)
        ).fetchone()
        none_row = conn.execute(
            "SELECT COUNT(*) AS n FROM user_progress WHERE form_id = ?", (went_id,)
        ).fetchone()

    assert used == ["thought"]
    assert row["n"] == 1
    assert none_row["n"] == 0


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
