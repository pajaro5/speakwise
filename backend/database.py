import sqlite3
from contextlib import contextmanager
from collections.abc import Generator, Iterator

from backend.config import load_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS words (
    id       INTEGER PRIMARY KEY,
    lemma    TEXT NOT NULL,
    rank     INTEGER,
    type     TEXT
);

CREATE TABLE IF NOT EXISTS word_forms (
    id         INTEGER PRIMARY KEY,
    word_id    INTEGER REFERENCES words(id),
    form       TEXT NOT NULL,
    tense      TEXT,
    phonemes   TEXT,
    lfc_focus  TEXT,
    stress_syl INTEGER
);

CREATE TABLE IF NOT EXISTS word_properties (
    word_id        INTEGER REFERENCES words(id),
    translation_es TEXT,
    register       TEXT,
    topic_tags     TEXT
);

CREATE TABLE IF NOT EXISTS chunks (
    id       INTEGER PRIMARY KEY,
    word_id  INTEGER REFERENCES words(id),
    chunk    TEXT NOT NULL,
    tense    TEXT,
    function TEXT,
    level    INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS phonetic_patterns (
    id       INTEGER PRIMARY KEY,
    name     TEXT,
    rule_es  TEXT,
    rule_ipa TEXT,
    family   TEXT,
    priority INTEGER
);

CREATE TABLE IF NOT EXISTS curriculum_plan (
    week          INTEGER,
    word_id       INTEGER REFERENCES words(id),
    phoneme_focus TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id                INTEGER PRIMARY KEY,
    date              TEXT,
    duration_sec      INTEGER,
    topic             TEXT,
    transcript        TEXT,
    wpm               REAL,
    fillers           INTEGER,
    comprehensibility REAL,
    chunk_used        TEXT,
    chunk_produced    INTEGER,
    chunk_spontaneous INTEGER,
    stress_correct    REAL,
    phoneme_errors    TEXT,
    pattern_focus     TEXT,
    feedback          TEXT,
    prompts_shown     INTEGER DEFAULT 0,
    prompts_used      INTEGER DEFAULT 0,
    prompt_ratio      REAL,
    panel_mode        TEXT,
    worksheet_path    TEXT
);

CREATE TABLE IF NOT EXISTS user_progress (
    id          INTEGER PRIMARY KEY,
    form_id     INTEGER REFERENCES word_forms(id),
    context     TEXT NOT NULL,
    exposures   INTEGER DEFAULT 0,
    last_seen   TEXT,
    score       REAL DEFAULT 0.0,
    next_review TEXT
);

CREATE TABLE IF NOT EXISTS pattern_progress (
    id                 INTEGER PRIMARY KEY,
    pattern_id         INTEGER REFERENCES phonetic_patterns(id),
    stage              INTEGER DEFAULT 1,
    accuracy           REAL DEFAULT 0.0,
    sessions_practiced INTEGER DEFAULT 0,
    last_seen          TEXT,
    next_review        TEXT
);

CREATE TABLE IF NOT EXISTS phoneme_log (
    id          INTEGER PRIMARY KEY,
    session_id  INTEGER REFERENCES sessions(id),
    word        TEXT,
    phoneme_exp TEXT,
    phoneme_got TEXT,
    correct     INTEGER
);

CREATE INDEX IF NOT EXISTS idx_progress_form    ON user_progress(form_id);
CREATE INDEX IF NOT EXISTS idx_progress_context ON user_progress(context, score);
CREATE INDEX IF NOT EXISTS idx_sessions_date    ON sessions(date);
CREATE INDEX IF NOT EXISTS idx_phoneme_word     ON phoneme_log(word);
CREATE INDEX IF NOT EXISTS idx_pattern_stage    ON pattern_progress(stage, accuracy);
"""


def _connect(db_path: str) -> sqlite3.Connection:
    # check_same_thread=False: FastAPI resuelve dependencias sync (get_db) en un
    # thread del threadpool distinto al del handler async que la usa. La conexión
    # solo se usa secuencialmente dentro del ciclo de vida de un mismo request.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    return conn


@contextmanager
def db_connection(db_path: str | None = None) -> Iterator[sqlite3.Connection]:
    path = db_path or load_settings().db_path
    conn = _connect(path)
    try:
        yield conn
    finally:
        conn.close()


def get_db() -> Generator[sqlite3.Connection, None, None]:
    with db_connection() as conn:
        yield conn


def create_session(
    conn: sqlite3.Connection,
    *,
    date: str,
    topic: str,
    transcript: str,
    wpm: float,
    fillers: int,
    feedback: str,
) -> int:
    cur = conn.execute(
        "INSERT INTO sessions (date, topic, transcript, wpm, fillers, feedback) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (date, topic, transcript, wpm, fillers, feedback),
    )
    conn.commit()
    return cur.lastrowid


def update_session(
    conn: sqlite3.Connection,
    session_id: int,
    *,
    transcript: str,
    wpm: float,
    fillers: int,
    feedback: str,
) -> None:
    conn.execute(
        "UPDATE sessions SET transcript = ?, wpm = ?, fillers = ?, feedback = ? "
        "WHERE id = ?",
        (transcript, wpm, fillers, feedback, session_id),
    )
    conn.commit()
