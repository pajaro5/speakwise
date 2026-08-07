import pytest

from backend import seed
from backend.database import db_connection
from backend.services.diagnostic import apply_diagnostic_results, build_diagnostic_plan


@pytest.fixture
def seeded_db_path(tmp_path) -> str:
    db_path = str(tmp_path / "diagnostic_test.db")
    seed.run(db_path)
    return db_path


def test_build_diagnostic_plan_covers_priority_1_patterns(seeded_db_path: str) -> None:
    """Fase D del plan de mejora (comparación vs ELSA/BoldVoice): ambas
    arrancan con un diagnóstico que identifica los puntos débiles reales
    del alumno, en vez de una rotación reactiva que arranca en frío. El
    diagnóstico cubre los patrones priority=1 (los de mayor impacto real
    para un hispanohablante, ver Fase A)."""
    with db_connection(seeded_db_path) as conn:
        plan = build_diagnostic_plan(conn)

    names = {p["name"] for p in plan}
    assert "schwa" in names
    assert "-age/-idge" not in names  # priority 2, no es de alto impacto
    for pattern in plan:
        assert pattern["words"], pattern["name"]
        assert all("*" not in w and "~" not in w for w in pattern["words"]), pattern["words"]


def test_apply_diagnostic_results_seeds_pattern_progress_per_pattern(
    seeded_db_path: str,
) -> None:
    with db_connection(seeded_db_path) as conn:
        plan = build_diagnostic_plan(conn)
        schwa = next(p for p in plan if p["name"] == "schwa")

        apply_diagnostic_results(
            conn,
            plan,
            transcript_text=" ".join(schwa["words"]),
            phoneme_errors=[{"word": schwa["words"][0], "expected": "x", "produced": "y"}],
        )

        row = conn.execute(
            "SELECT accuracy, sessions_practiced FROM pattern_progress WHERE pattern_id = ?",
            (schwa["pattern_id"],),
        ).fetchone()

    assert row is not None
    assert row["sessions_practiced"] == 1
    expected_accuracy = (len(schwa["words"]) - 1) / len(schwa["words"])
    assert row["accuracy"] == pytest.approx(expected_accuracy)


def test_apply_diagnostic_results_skips_patterns_with_no_attempted_words(
    seeded_db_path: str,
) -> None:
    """Si ninguna palabra de un patrón aparece en la transcripción (el
    alumno no llegó a decirla, o se cortó la grabación), no se inventa un
    resultado — mismo criterio ya establecido para pattern_progress/
    user_progress: sin evidencia real, no se actualiza nada."""
    with db_connection(seeded_db_path) as conn:
        plan = build_diagnostic_plan(conn)

        apply_diagnostic_results(
            conn, plan, transcript_text="completely unrelated silence", phoneme_errors=[]
        )

        count = conn.execute("SELECT COUNT(*) AS n FROM pattern_progress").fetchone()["n"]

    assert count == 0
