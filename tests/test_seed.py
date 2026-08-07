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


def test_phonetic_patterns_exactly_13(seeded_db_path: str) -> None:
    """El usuario pidió una comparación rigurosa contra ELSA Speak/Loora y
    un plan de mejora. Fase A: 5 patrones nuevos respaldados por análisis
    contrastivo español→inglés (ɪ/iː, v/b, θ/ð, consonante final,
    epéntesis de e- antes de s+consonante), de mayor impacto real para un
    hispanohablante que algunos de los patrones anteriores (más
    "curiosidad ortográfica" que error frecuente). Fase B: 2 patrones de
    enlace entre palabras (linking/reducciones), el fenómeno más frecuente
    en habla real y que antes no se cubría en absoluto (solo dentro de
    una palabra, nunca entre palabras)."""
    with db_connection(seeded_db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM phonetic_patterns").fetchone()[0]

    assert count == 13


def test_chunks_are_curated_idioms_with_meaning(seeded_db_path: str) -> None:
    """El usuario reportó que el "chunk of the day" generado por plantilla
    ("I think this every day.") no aporta valor real — pidió reemplazarlo
    por expresiones idiomáticas de uso real, con su significado explicado.
    Ya no se generan mecánicamente por palabra×tiempo verbal (200+ filas),
    ahora vienen curadas a mano desde corpus/idioms.csv, con meaning_es."""
    with db_connection(seeded_db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        missing = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE function IS NULL OR meaning_es IS NULL"
        ).fetchone()[0]

    assert total >= 25
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
    assert patterns == 13
    assert chunks >= 25


def test_lfc_focus_is_the_primary_stressed_vowel() -> None:
    phonemes = ["TH", "AO1", "T"]
    lfc_focus, stress_syl = seed._lfc_focus_and_stress(phonemes)

    assert lfc_focus == "AO1"
    assert stress_syl == 0


def test_idioms_are_not_tied_to_a_vocab_word(seeded_db_path: str) -> None:
    """Los modismos ya no están atados a una palabra del top-150 (a
    diferencia del drilling de gramática anterior) — word_id queda NULL,
    _chunk_of_the_day() ya no hace JOIN contra words."""
    with db_connection(seeded_db_path) as conn:
        row = conn.execute(
            "SELECT word_id FROM chunks WHERE chunk LIKE 'Not my circus%'"
        ).fetchone()

    assert row is not None
    assert row["word_id"] is None


def test_reseeding_removes_old_word_based_chunks(tmp_path) -> None:
    """Bug real encontrado en vivo: una DB ya seedeada con la versión
    anterior (chunks generados por plantilla word×tiempo, ej. "Yesterday I
    was tired.", con word_id NOT NULL) seguía sirviendo esos chunks viejos
    como "el de hoy" después de reseedear con los modismos nuevos — nunca
    se borraban, solo se agregaban los nuevos al lado. Como todos
    empataban en spontaneous_uses/produced_uses=0, el desempate por id
    terminaba eligiendo uno de los viejos (ids más bajos)."""
    db_path = str(tmp_path / "seed_test.db")
    seed.run(db_path)
    with db_connection(db_path) as conn:
        word_id = conn.execute("SELECT id FROM words LIMIT 1").fetchone()["id"]
        conn.execute(
            "INSERT INTO chunks (word_id, chunk, tense, function, level) "
            "VALUES (?, 'Yesterday I was tired.', 'past', 'past_narration', 1)",
            (word_id,),
        )
        conn.commit()

    seed.run(db_path)

    with db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM chunks WHERE word_id IS NOT NULL"
        ).fetchone()

    assert row["n"] == 0


def test_reseeding_updates_idiom_meaning_without_duplicating(tmp_path) -> None:
    """Re-seedear una DB que ya tiene el modismo (con un meaning_es viejo)
    debe actualizarlo, no duplicarlo — mismo patrón ya establecido para
    chunks/patterns (identificado por el texto del chunk, que es único)."""
    db_path = str(tmp_path / "seed_test.db")
    seed.run(db_path)
    with db_connection(db_path) as conn:
        conn.execute(
            "UPDATE chunks SET meaning_es = 'significado viejo' "
            "WHERE chunk = 'Piece of cake.'"
        )
        conn.commit()

    seed.run(db_path)

    with db_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT meaning_es FROM chunks WHERE chunk = 'Piece of cake.'"
        ).fetchall()
    assert len(rows) == 1, rows
    assert rows[0]["meaning_es"] != "significado viejo"


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
    for word in by_name["t muda después de n"]:
        assert "~" in word, f"falta marcar la t muda en {word!r}"
    for word in by_name["vocal corta i vs. larga i"]:
        assert "*" in word, f"falta resaltar la vocal en {word!r}"
    for word in by_name["v no es b"]:
        assert "*" in word, f"falta resaltar la v en {word!r}"
    for word in by_name["th no es s/t/d"]:
        assert "*" in word, f"falta resaltar el th en {word!r}"
    for word in by_name["consonante final que se cae"]:
        assert "*" in word, f"falta resaltar la consonante final en {word!r}"
    for word in by_name["sin e antes de s+consonante"]:
        assert "*" in word, f"falta resaltar la s inicial en {word!r}"
    for word in by_name["enlace entre palabras"]:
        assert "*" in word, f"falta resaltar el enlace en {word!r}"
    for word in by_name["reducciones con 'to'"]:
        assert "*" in word, f"falta resaltar la reducción en {word!r}"


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


def test_pattern_family_stress_matches_family_length(seeded_db_path: str) -> None:
    """El usuario pidió mostrar la sílaba tónica en mayúsculas (ej.
    "aVERage") — curado a mano en patterns.csv (family_stress), igual que
    el markup ~x~/*x* (family), porque una syllabificación ortográfica
    general no es confiable (probado con pyphen antes de decidir esto)."""
    import json

    with db_connection(seeded_db_path) as conn:
        rows = conn.execute(
            "SELECT name, family, family_stress FROM phonetic_patterns"
        ).fetchall()

    for row in rows:
        family = json.loads(row["family"])
        family_stress = json.loads(row["family_stress"])
        assert len(family_stress) == len(family), row["name"]


def test_reseeding_updates_pattern_family_stress(tmp_path) -> None:
    db_path = str(tmp_path / "seed_test2.db")
    seed.run(db_path)
    with db_connection(db_path) as conn:
        conn.execute(
            "UPDATE phonetic_patterns SET family_stress = '[\"different\"]' "
            "WHERE name = '-age/-idge'"
        )
        conn.commit()

    seed.run(db_path)

    with db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT family_stress FROM phonetic_patterns WHERE name = '-age/-idge'"
        ).fetchone()
    assert "AVerage" in row["family_stress"]
