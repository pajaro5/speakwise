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


def test_be_chunks_are_grammatical(tmp_path) -> None:
    """El template genérico produce "I be this every day." para el verbo
    irregular "be" — no es gramatical y el usuario reportó que no sabía qué
    decir por falta de contexto. "be" necesita chunks curados a mano."""
    db_path = str(tmp_path / "seed_test.db")
    seed.run(db_path)
    with db_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT chunk FROM chunks c JOIN words w ON w.id = c.word_id "
            "WHERE w.lemma = 'be'"
        ).fetchall()
    chunks = [r["chunk"] for r in rows]
    assert not any(c.startswith("I be ") for c in chunks), chunks
    assert not any(c.startswith("I'm being it") for c in chunks), chunks
    assert not any(c == "Yesterday I was it." for c in chunks), chunks


def test_reseeding_an_already_seeded_db_does_not_duplicate_overridden_chunks(tmp_path) -> None:
    """Re-seedear una DB que ya tiene el chunk viejo (creado antes de que
    existiera IRREGULAR_CHUNKS, con function="habit") no debe dejarlo
    huérfano junto al nuevo — debe reemplazarlo, no duplicarlo. Reproduce
    el estado real que tenía la DB del usuario."""
    db_path = str(tmp_path / "seed_test.db")
    seed.run(db_path)
    with db_connection(db_path) as conn:
        conn.execute(
            "UPDATE chunks SET chunk = 'I be this every day.', function = 'habit' "
            "WHERE word_id = (SELECT id FROM words WHERE lemma = 'be') AND tense = 'base'"
        )
        conn.commit()

    seed.run(db_path)

    with db_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT chunk FROM chunks c JOIN words w ON w.id = c.word_id "
            "WHERE w.lemma = 'be' AND c.tense = 'base'"
        ).fetchall()
    assert len(rows) == 1, [r["chunk"] for r in rows]
    assert rows[0]["chunk"] == "Be careful with that."


def test_pattern_family_words_have_marked_syllables(seeded_db_path: str) -> None:
    """Reportado por el usuario: en "sílabas elididas" no queda claro cuál
    sílaba no se pronuncia. Se agrega markup a las palabras de ejemplo:
    ~x~ = letra/sílaba silenciosa, *x* = parte resaltada (pronunciación
    distinta a la escrita, pero no muda)."""
    import json

    with db_connection(seeded_db_path) as conn:
        rows = conn.execute("SELECT name, family FROM phonetic_patterns").fetchall()

    by_name = {r["name"]: json.loads(r["family"]) for r in rows}

    for word in by_name["sílabas elididas"]:
        assert "~" in word, f"falta marcar la sílaba muda en {word!r}"
    for word in by_name["letras mudas kn-/wr-"]:
        assert "~" in word, f"falta marcar la letra muda en {word!r}"
    for word in by_name["-age/-idge"]:
        assert "*" in word, f"falta resaltar el sufijo en {word!r}"
    for word in by_name["-tion/-sion"]:
        assert "*" in word, f"falta resaltar el sufijo en {word!r}"
    for word in by_name["schwa"]:
        assert "*" in word, f"falta resaltar la vocal átona en {word!r}"


def test_reseeding_updates_pattern_family_markup(tmp_path) -> None:
    """Re-seedear una DB que ya tiene los patterns con el family viejo (sin
    markup) debe actualizarlo, no dejarlo como estaba — mismo problema que
    tuvieron los chunks de "be"."""
    db_path = str(tmp_path / "seed_test.db")
    seed.run(db_path)
    with db_connection(db_path) as conn:
        conn.execute(
            "UPDATE phonetic_patterns SET family = '[\"different\", \"chocolate\"]' "
            "WHERE name = 'sílabas elididas'"
        )
        conn.commit()

    seed.run(db_path)

    with db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT family FROM phonetic_patterns WHERE name = 'sílabas elididas'"
        ).fetchone()
    assert "~" in row["family"]
