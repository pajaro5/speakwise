import csv
import sqlite3
from pathlib import Path

import cmudict

from backend.database import db_connection

CORPUS_DIR = Path(__file__).resolve().parent.parent / "corpus"

TENSES = ["base", "third_sg", "progressive", "past", "past_participle"]

_cmu = cmudict.dict()


def _phonemes_for(word: str) -> list[str]:
    entries = _cmu.get(word.lower())
    if not entries:
        raise ValueError(f"'{word}' no está en cmudict — no se puede derivar phonemes")
    return entries[0]


def _lfc_focus_and_stress(phonemes: list[str]) -> tuple[str, int]:
    vowels = [p for p in phonemes if p[-1].isdigit()]
    for idx, p in enumerate(vowels):
        if p.endswith("1"):
            return p, idx
    return vowels[0], 0


def load_words_csv() -> list[dict]:
    with open(CORPUS_DIR / "words.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_patterns_csv() -> list[dict]:
    with open(CORPUS_DIR / "patterns.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_idioms_csv() -> list[dict]:
    with open(CORPUS_DIR / "idioms.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def seed_words(conn: sqlite3.Connection, rows: list[dict]) -> None:
    for row in rows:
        existing = conn.execute(
            "SELECT id FROM words WHERE lemma = ?", (row["lemma"],)
        ).fetchone()
        if existing:
            word_id = existing["id"]
        else:
            cur = conn.execute(
                "INSERT INTO words (lemma, rank, type) VALUES (?, ?, ?)",
                (row["lemma"], int(row["rank"]), row["type"]),
            )
            word_id = cur.lastrowid
            conn.execute(
                "INSERT INTO word_properties (word_id, translation_es, register, topic_tags) "
                "VALUES (?, ?, ?, ?)",
                (word_id, row["translation_es"], row["register"], row["topic_tags"]),
            )

        for tense in TENSES:
            form = row[tense]
            already = conn.execute(
                "SELECT id FROM word_forms WHERE word_id = ? AND tense = ?",
                (word_id, tense),
            ).fetchone()
            if already:
                continue
            phonemes = _phonemes_for(form)
            lfc_focus, stress_syl = _lfc_focus_and_stress(phonemes)
            conn.execute(
                "INSERT INTO word_forms "
                "(word_id, form, tense, phonemes, lfc_focus, stress_syl) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (word_id, form, tense, " ".join(phonemes), lfc_focus, stress_syl),
            )
    conn.commit()


def seed_patterns(conn: sqlite3.Connection, rows: list[dict]) -> None:
    for row in rows:
        existing = conn.execute(
            "SELECT id FROM phonetic_patterns WHERE name = ?", (row["name"],)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE phonetic_patterns SET rule_es = ?, rule_ipa = ?, family = ?, "
                "priority = ?, family_stress = ? WHERE id = ?",
                (
                    row["rule_es"],
                    row["rule_ipa"],
                    row["family"],
                    int(row["priority"]),
                    row["family_stress"],
                    existing["id"],
                ),
            )
            continue
        conn.execute(
            "INSERT INTO phonetic_patterns (name, rule_es, rule_ipa, family, priority, "
            "family_stress) VALUES (?, ?, ?, ?, ?, ?)",
            (
                row["name"],
                row["rule_es"],
                row["rule_ipa"],
                row["family"],
                int(row["priority"]),
                row["family_stress"],
            ),
        )
    conn.commit()


def seed_chunks(conn: sqlite3.Connection, rows: list[dict]) -> None:
    """El "chunk of the day" ya no se genera por plantilla a partir del
    vocabulario (word×tense, ej. "I think this every day.") — el usuario
    reportó que eso no aporta valor real de conversación, y pidió
    expresiones idiomáticas de uso real con su significado explicado.
    Cada modismo se identifica por su propio texto (no depende de una
    palabra del corpus — word_id/tense quedan NULL). Los chunks viejos
    (word_id NOT NULL, generados por la versión anterior) se borran acá —
    bug real encontrado en vivo: si se dejaban, seguían empatando con los
    modismos nuevos en spontaneous_uses/produced_uses=0 y a veces ganaban
    el desempate por id, así que el chunk "de hoy" seguía siendo uno
    viejo aunque el corpus ya no lo generara más."""
    conn.execute("DELETE FROM chunks WHERE word_id IS NOT NULL")
    for row in rows:
        existing = conn.execute(
            "SELECT id FROM chunks WHERE chunk = ?", (row["idiom"],)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE chunks SET function = ?, meaning_es = ? WHERE id = ?",
                (row["function"], row["meaning_es"], existing["id"]),
            )
            continue
        conn.execute(
            "INSERT INTO chunks (chunk, function, meaning_es, level) VALUES (?, ?, ?, ?)",
            (row["idiom"], row["function"], row["meaning_es"], 1),
        )
    conn.commit()


def run(db_path: str | None = None) -> None:
    words = load_words_csv()
    patterns = load_patterns_csv()
    idioms = load_idioms_csv()
    with db_connection(db_path) as conn:
        seed_words(conn, words)
        seed_patterns(conn, patterns)
        seed_chunks(conn, idioms)


if __name__ == "__main__":
    run()
