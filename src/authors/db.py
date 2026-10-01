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
    note            TEXT,
    name_type       TEXT CHECK (name_type IN   -- qué nombre del autor usa el seed (se rellena en enrich)
                        ('pseudonym','main','birth_name','alias','other'))
);

CREATE TABLE IF NOT EXISTS authors (
    qid                 TEXT PRIMARY KEY,
    label               TEXT,              -- etiqueta en inglés (fallback: mul, español)
    label_es            TEXT,
    description         TEXT,              -- descripción en inglés (fallback: español)
    birth_date          TEXT,              -- ISO truncada a la precisión; '-0630' = 630 a.C.
    birth_year          INTEGER,           -- año histórico; negativo = a.C.
    birth_precision     TEXT,              -- day | month | year | decade | century | millennium
    birth_calendar      TEXT,              -- gregorian | julian (tal cual en Wikidata)
    death_date          TEXT,
    death_year          INTEGER,
    death_precision     TEXT,
    death_calendar      TEXT,
    birth_place_qid     TEXT,
    birth_place         TEXT,
    death_place_qid     TEXT,
    death_place         TEXT,
    gender              TEXT,
    sitelinks           INTEGER,
    viaf_id             TEXT,              -- IDs externos: multivalor, separados por ' | '
    isni                TEXT,
    openlibrary_id      TEXT,
    goodreads_id        TEXT,
    wikipedia_en        TEXT,
    wikipedia_es        TEXT,
    conflicting_fields  TEXT,              -- género/lugares/fechas con >1 valor de mejor rango
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

-- Correcciones manuales aplicadas sobre datos de Wikidata (data/corrections.csv).
CREATE TABLE IF NOT EXISTS author_corrections (
    qid             TEXT NOT NULL REFERENCES authors(qid),
    field           TEXT NOT NULL,         -- columna de authors o 'remove_name'
    original_value  TEXT,                  -- valor tal como venía de Wikidata
    corrected_value TEXT,                  -- NULL si se eliminó
    reason          TEXT NOT NULL
);

-- Vista plana: una fila por autor, multivalores separados por ' | '.
CREATE VIEW IF NOT EXISTS v_authors_flat AS
SELECT
    a.*,
    (SELECT group_concat(s.clean_name, ' | ') FROM seed_resolution r
       JOIN seed_names s USING (seed_id) WHERE r.qid = a.qid)            AS seed_names,
    (SELECT group_concat(occupation, ' | ') FROM
       (SELECT occupation FROM author_occupations o WHERE o.qid = a.qid ORDER BY occupation)) AS occupations,
    (SELECT group_concat(country, ' | ') FROM
       (SELECT country FROM author_citizenships c WHERE c.qid = a.qid ORDER BY country))    AS citizenships,
    (SELECT group_concat(language, ' | ') FROM
       (SELECT language FROM author_languages l WHERE l.qid = a.qid ORDER BY language))     AS languages,
    (SELECT group_concat(name, ' | ') FROM
       (SELECT name FROM author_names n WHERE n.qid = a.qid AND n.kind = 'pseudonym' ORDER BY name)) AS pseudonyms
FROM authors a;

-- Trazabilidad fila del seed -> autor.
CREATE VIEW IF NOT EXISTS v_seed_resolution AS
SELECT s.seed_id, s.raw_name AS author_name, r.status, r.method,
       round(r.confidence, 3) AS confidence, r.qid, r.name_type, a.label AS wikidata_label,
       a.description AS wikidata_description, r.note
FROM seed_names s
LEFT JOIN seed_resolution r USING (seed_id)
LEFT JOIN authors a ON a.qid = r.qid;
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn
