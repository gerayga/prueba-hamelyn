"""Esquema SQLite y helpers de conexión."""
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS seed_names (
    seed_id         INTEGER PRIMARY KEY,   -- nº de fila en el CSV (1-based)
    raw_name        TEXT NOT NULL,         -- tal cual viene en el seed
    clean_name      TEXT NOT NULL,         -- NFC + espacios normalizados
    match_key       TEXT NOT NULL          -- sin tildes/puntuación, para comparar
);

-- Candidatos devueltos por Wikidata para cada nombre del seed.
CREATE TABLE IF NOT EXISTS candidates (
    seed_id         INTEGER NOT NULL REFERENCES seed_names(seed_id),
    qid             TEXT NOT NULL,
    search_rank     INTEGER NOT NULL,      -- posición en la búsqueda
    label           TEXT,
    description     TEXT,
    is_human        INTEGER NOT NULL,
    is_writer       INTEGER NOT NULL,
    name_match      TEXT NOT NULL,         -- exact_label | alias | partial
    source          TEXT NOT NULL,         -- search | fulltext
    sitelinks       INTEGER NOT NULL,
    score           REAL NOT NULL,
    PRIMARY KEY (seed_id, qid)
);

-- Decisión final por fila del seed.
CREATE TABLE IF NOT EXISTS seed_resolution (
    seed_id         INTEGER PRIMARY KEY REFERENCES seed_names(seed_id),
    qid             TEXT,                  -- NULL si no hay match
    status          TEXT NOT NULL CHECK (status IN
                        ('matched','ambiguous','no_match','not_a_person')),
    method          TEXT NOT NULL,         -- exact_label | alias | partial | fulltext | override | rule | none
    confidence      REAL,                  -- 0..1
    note            TEXT
);

CREATE TABLE IF NOT EXISTS authors (
    qid                 TEXT PRIMARY KEY,
    label               TEXT,
    description         TEXT,
    birth_date          TEXT,              -- ISO; año negativo = a.C.
    birth_precision     TEXT,              -- day | month | year | decade | century | millennium
    death_date          TEXT,
    death_precision     TEXT,
    birth_place_qid     TEXT,
    birth_place         TEXT,
    death_place_qid     TEXT,
    death_place         TEXT,
    gender              TEXT,
    sitelinks           INTEGER,
    viaf_id             TEXT,
    isni                TEXT,
    openlibrary_id      TEXT,
    goodreads_id        TEXT,
    wikipedia_en        TEXT,
    wikipedia_es        TEXT,
    retrieved_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS author_occupations (
    qid TEXT NOT NULL REFERENCES authors(qid),
    occupation_qid TEXT NOT NULL,
    occupation TEXT,
    PRIMARY KEY (qid, occupation_qid)
);

CREATE TABLE IF NOT EXISTS author_citizenships (
    qid TEXT NOT NULL REFERENCES authors(qid),
    country_qid TEXT NOT NULL,
    country TEXT,
    PRIMARY KEY (qid, country_qid)
);

CREATE TABLE IF NOT EXISTS author_languages (
    qid TEXT NOT NULL REFERENCES authors(qid),
    language_qid TEXT NOT NULL,
    language TEXT,
    PRIMARY KEY (qid, language_qid)
);

CREATE TABLE IF NOT EXISTS author_names (
    qid TEXT NOT NULL REFERENCES authors(qid),
    name TEXT NOT NULL,
    kind TEXT NOT NULL,                    -- alias | pseudonym | birth_name
    lang TEXT,
    PRIMARY KEY (qid, name, kind)
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn
