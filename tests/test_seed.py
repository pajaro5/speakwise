import re

import pytest

from backend import seed
from backend.database import db_connection

ARPABET_RE = re.compile(r"^[A-Z]+[0-2]?( [A-Z]+[0-2]?)*$")


@pytest.fixture
def seeded_db_path(tmp_path) -> str:
    db_path = str(tmp_path / "seed_test.db")
    seed.run(db_path)
    return db_path


def test_word_forms_at_least_150(seeded_db_path: str) -> None:
    with db_connection(seeded_db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM word_forms").fetchone()[0]

    assert count >= 150


def test_every_word_form_has_arpabet_phonemes_and_lfc_focus(seeded_db_path: str) -> None:
    with db_connection(seeded_db_path) as conn:
        rows = conn.execute("SELECT phonemes, lfc_focus FROM word_forms").fetchall()

    assert len(rows) > 0
    for row in rows:
        assert row["phonemes"], "phonemes no debe estar vacío"
        assert ARPABET_RE.match(row["phonemes"]), f"formato ARPAbet inválido: {row['phonemes']!r}"
        assert row["lfc_focus"], "lfc_focus no debe estar vacío"


def test_phonetic_patterns_exactly_5(seeded_db_path: str) -> None:
    with db_connection(seeded_db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM phonetic_patterns").fetchone()[0]

    assert count == 5


def test_chunks_at_least_150_with_function_and_level(seeded_db_path: str) -> None:
    with db_connection(seeded_db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        missing = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE function IS NULL OR level IS NULL"
        ).fetchone()[0]

    assert total >= 150
    assert missing == 0


def test_seed_is_idempotent(seeded_db_path: str) -> None:
    seed.run(seeded_db_path)  # correr una segunda vez

    with db_connection(seeded_db_path) as conn:
        words = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
        forms = conn.execute("SELECT COUNT(*) FROM word_forms").fetchone()[0]
        patterns = conn.execute("SELECT COUNT(*) FROM phonetic_patterns").fetchone()[0]
        chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    assert words == 50
    assert forms >= 150
    assert patterns == 5
    assert chunks >= 150


def test_lfc_focus_is_the_primary_stressed_vowel() -> None:
    phonemes = ["TH", "AO1", "T"]
    lfc_focus, stress_syl = seed._lfc_focus_and_stress(phonemes)

    assert lfc_focus == "AO1"
    assert stress_syl == 0
