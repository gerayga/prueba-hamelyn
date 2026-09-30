"""Resolución nombre del seed -> QID de Wikidata.

Flujo por nombre:
  1. Regla de no-persona ('Anonymous', 'Various Authors') -> sin llamada a la API.
  2. Candidatos con wbsearchentities (en + es). Si ninguno es humano, fallback
     de texto completo restringido a humanos (P31=Q5).
  3. Hechos de cada candidato por SPARQL (humano, ocupación literaria, obras
     con P50, nº de sitelinks) y puntuación.
  4. Decisión matched / ambiguous / no_match.
  5. Los overrides manuales (data/overrides.csv) se aplican al final y ganan.
"""
import csv
import logging
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from authors.normalize import match_key
from authors.wikidata import WikidataClient

log = logging.getLogger(__name__)

SEARCH_LANGS = ("en", "es")
NON_PERSON_KEYS = {"anonymous", "anonimo", "various authors", "varios autores", "unknown"}

# Ocupaciones (y sus subclases, vía P279*) que consideramos "autor de libros".
LITERARY_OCCUPATIONS = {
    "Q36180": "writer",
    "Q4964182": "philosopher",
    "Q201788": "historian",
}

# Pesos y umbrales. Heurísticos, documentados en el README.
W_NAME, W_LITERARY, W_POPULARITY = 0.40, 0.35, 0.25
NAME_SCORES = {"exact_label": 1.0, "alias": 0.8, "partial": 0.3}
MATCH_THRESHOLD = 0.60
MIN_MARGIN = 0.15
# Si el mejor candidato tiene >= N veces los sitelinks del segundo, el margen de
# score no se exige: el homónimo es una figura muy menor (p.ej. el padre de John Milton).
DOMINANCE_RATIO = 5

# Clases P31 que aceptamos como "persona". Q21070568 = humano cuya existencia se
# discute (Homero); sin ella Homer se resolvía a Winslow Homer.
HUMAN_CLASSES = ("Q5", "Q21070568")


@dataclass
class Candidate:
    qid: str
    search_rank: int
    label: str | None
    description: str | None
    name_match: str
    source: str = "search"                 # search | fulltext
    is_human: bool = False
    is_writer: bool = False
    has_works: bool = False
    sitelinks: int = 0
    score: float = 0.0


def classify_name_match(query_key: str, label: str | None,
                        match_type: str | None, match_text: str | None) -> str:
    """exact_label si la etiqueta coincide; alias si coincide el texto con el que
    la API encontró la entidad; partial en otro caso (búsqueda por prefijo)."""
    if label and match_key(label) == query_key:
        return "exact_label"
    if match_text and match_key(match_text) == query_key:
        return "alias" if match_type == "alias" else "exact_label"
    return "partial"


def score_candidate(c: Candidate) -> float:
    if not c.is_human:
        return 0.0
    literary = 1.0 if c.is_writer else 0.5 if c.has_works else 0.0
    popularity = min(math.log10(c.sitelinks + 1) / 2.5, 1.0)
    return round(
        W_NAME * NAME_SCORES[c.name_match] + W_LITERARY * literary + W_POPULARITY * popularity, 4
    )


def decide(cands: list[Candidate]) -> tuple[str, Candidate | None, float | None, str]:
    """Devuelve (status, mejor_candidato, confianza, nota)."""
    ranked = sorted((c for c in cands if c.score > 0), key=lambda c: c.score, reverse=True)
    if not ranked:
        return "no_match", None, None, "ningún candidato humano"
    best = ranked[0]
    runner_up = ranked[1] if len(ranked) > 1 else None
    margin = best.score - (runner_up.score if runner_up else 0.0)
    dominant = runner_up is None or best.sitelinks >= DOMINANCE_RATIO * max(runner_up.sitelinks, 1)
    notes = []
    if not (best.is_writer or best.has_works):
        notes.append("sin ocupación literaria ni obras P50")
    if best.score < MATCH_THRESHOLD:
        notes.append(f"score {best.score:.2f} < {MATCH_THRESHOLD}")
    if margin < MIN_MARGIN and not dominant:
        notes.append(f"margen {margin:.2f} con {runner_up.qid} ({runner_up.label}), "
                     f"sitelinks {best.sitelinks} vs {runner_up.sitelinks}")
    status = "ambiguous" if notes else "matched"
    return status, best, best.score, "; ".join(notes)


# --- recogida de candidatos -------------------------------------------------

def search_candidates(client: WikidataClient, name: str) -> list[Candidate]:
    key = match_key(name)
    found: dict[str, Candidate] = {}
    for lang in SEARCH_LANGS:
        for rank, hit in enumerate(client.search_entities(name, lang)):
            m = hit.get("match", {})
            nm = classify_name_match(key, hit.get("label"), m.get("type"), m.get("text"))
            prev = found.get(hit["id"])
            if prev is None:
                found[hit["id"]] = Candidate(
                    hit["id"], rank, hit.get("label"), hit.get("description"), nm)
            else:
                prev.search_rank = min(prev.search_rank, rank)
                if NAME_SCORES[nm] > NAME_SCORES[prev.name_match]:
                    prev.name_match = nm
    return list(found.values())


def fulltext_candidates(client: WikidataClient, name: str) -> list[Candidate]:
    return [
        Candidate(hit["title"], rank, None, None, "partial", source="fulltext")
        for rank, hit in enumerate(client.fulltext_humans(name))
    ]


def fetch_facts(client: WikidataClient, qids: list[str], batch: int = 150) -> dict[str, dict]:
    facts: dict[str, dict] = {}
    occ_values = " ".join(f"wd:{q}" for q in LITERARY_OCCUPATIONS)
    human_values = " ".join(f"wd:{q}" for q in HUMAN_CLASSES)
    qids = sorted(set(qids))
    for i in range(0, len(qids), batch):
        values = " ".join(f"wd:{q}" for q in qids[i:i + batch])
        query = f"""
SELECT ?item ?sitelinks ?human ?writer ?works ?label WHERE {{
  VALUES ?item {{ {values} }}
  OPTIONAL {{ ?item wikibase:sitelinks ?sitelinks }}
  OPTIONAL {{ ?item rdfs:label ?label FILTER(LANG(?label) IN ("en", "mul")) }}
  BIND(EXISTS {{ ?item wdt:P31 ?cls VALUES ?cls {{ {human_values} }} }} AS ?human)
  BIND(EXISTS {{ ?item wdt:P106/wdt:P279* ?occ VALUES ?occ {{ {occ_values} }} }} AS ?writer)
  BIND(EXISTS {{ ?work wdt:P50 ?item }} AS ?works)
}}"""
        for row in client.sparql(query):
            qid = row["item"]["value"].rsplit("/", 1)[-1]
            facts[qid] = {
                "sitelinks": int(row.get("sitelinks", {}).get("value", 0)),
                "human": row["human"]["value"] == "true",
                "writer": row["writer"]["value"] == "true",
                "works": row["works"]["value"] == "true",
                "label": row.get("label", {}).get("value"),
            }
    return facts


def load_overrides(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8", newline="") as f:
        return {match_key(r["author_name"]): r for r in csv.DictReader(f) if r["author_name"].strip()}


# --- orquestación -----------------------------------------------------------

def run(conn: sqlite3.Connection, client: WikidataClient, overrides_path: Path,
        limit: int | None = None) -> None:
    seeds = conn.execute(
        "SELECT seed_id, clean_name, match_key FROM seed_names ORDER BY seed_id"
        + (f" LIMIT {int(limit)}" if limit else "")
    ).fetchall()
    overrides = load_overrides(overrides_path)

    per_seed: dict[int, list[Candidate]] = {}
    for n, s in enumerate(seeds, 1):
        if s["match_key"] in NON_PERSON_KEYS:
            continue
        cands = search_candidates(client, s["clean_name"])
        per_seed[s["seed_id"]] = cands
        if n % 50 == 0:
            log.info("Buscados %d/%d nombres", n, len(seeds))

    def apply_facts(cands_by_seed: dict[int, list[Candidate]]) -> None:
        facts = fetch_facts(client, [c.qid for cs in cands_by_seed.values() for c in cs])
        for cs in cands_by_seed.values():
            for c in cs:
                f = facts.get(c.qid, {})
                c.is_human = f.get("human", False)
                c.is_writer = f.get("writer", False)
                c.has_works = f.get("works", False)
                c.sitelinks = f.get("sitelinks", 0)
                c.label = c.label or f.get("label")
                c.score = score_candidate(c)

    apply_facts(per_seed)

    # Fallback de texto completo para los que no tienen ningún candidato humano.
    fallback: dict[int, list[Candidate]] = {}
    for s in seeds:
        cs = per_seed.get(s["seed_id"])
        if cs is not None and not any(c.is_human for c in cs):
            fallback[s["seed_id"]] = fulltext_candidates(client, s["clean_name"])
    if fallback:
        log.info("Fallback de texto completo para %d nombres", len(fallback))
        apply_facts(fallback)
        for sid, cs in fallback.items():
            known = {c.qid for c in per_seed[sid]}
            per_seed[sid].extend(c for c in cs if c.qid not in known)

    with conn:
        ids = [s["seed_id"] for s in seeds]
        marks = ",".join("?" * len(ids))
        conn.execute(f"DELETE FROM candidates WHERE seed_id IN ({marks})", ids)
        conn.execute(f"DELETE FROM seed_resolution WHERE seed_id IN ({marks})", ids)

        for s in seeds:
            sid = s["seed_id"]
            cands = per_seed.get(sid, [])
            conn.executemany(
                """INSERT INTO candidates (seed_id, qid, search_rank, label, description,
                   is_human, is_writer, name_match, source, sitelinks, score)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                [(sid, c.qid, c.search_rank, c.label, c.description, int(c.is_human),
                  int(c.is_writer or c.has_works), c.name_match, c.source, c.sitelinks, c.score)
                 for c in cands],
            )

            if s["match_key"] in NON_PERSON_KEYS:
                row = (sid, None, "not_a_person", "rule", None, "nombre genérico, no es una persona")
            else:
                status, best, conf, note = decide(cands)
                if best is None:
                    method = "none"
                else:
                    method = "fulltext" if best.source == "fulltext" else best.name_match
                row = (sid, best.qid if best else None, status, method, conf, note or None)

            ov = overrides.get(s["match_key"])
            if ov:
                qid = ov["qid"].strip() or None
                status = "matched" if qid else "no_match"
                row = (sid, qid, status, "override", 1.0 if qid else None,
                       f"override manual: {ov['reason']}")

            conn.execute(
                "INSERT INTO seed_resolution (seed_id, qid, status, method, confidence, note)"
                " VALUES (?,?,?,?,?,?)", row)

    log.info("Resolución: %d peticiones desde caché, %d nuevas", client.hits, client.misses)
