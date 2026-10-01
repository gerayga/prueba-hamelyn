"""Enriquecimiento QID -> atributos del autor.

- Propiedades con valor entidad/identificador: SPARQL por lotes (con rango).
- Fechas de nacimiento/muerte: wbgetclaims (JSON original). El SPARQL
  desplaza los años a.C. y convierte las fechas julianas, así que no sirve.

Selección de valores (semántica "best rank" de Wikidata): se descartan los
deprecated; si hay preferred solo cuentan los preferred. En campos
univaluados (género, lugares, fechas), si quedan varios valores distintos se
elige de forma determinista (fecha más precisa; si no, menor QID) y se anota el
campo en `conflicting_fields`. Los IDs externos (VIAF, ISNI...) son legítimamente
multivalor: se guardan todos, ordenados y separados por ' | '.
"""
import csv
import logging
import sqlite3
from collections import defaultdict
from pathlib import Path

from authors.normalize import CALENDARS, PRECISION_NAMES, match_key, parse_wikidata_time
from authors.wikidata import WikidataClient

log = logging.getLogger(__name__)

BATCH = 100
RANK_URI = "http://wikiba.se/ontology#"

# pid -> nombre lógico
SINGLE = {"P21": "gender", "P19": "birth_place", "P20": "death_place"}
EXTERNAL_IDS = {"P214": "viaf_id", "P213": "isni", "P648": "openlibrary_id", "P2963": "goodreads_id"}
MULTI = {"P106": "occupation", "P27": "citizenship", "P1412": "language",
         "P742": "pseudonym", "P1477": "birth_name"}


def _values(qids: list[str]) -> str:
    return " ".join(f"wd:{q}" for q in qids)


def _qid(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def _qnum(qid: str) -> tuple[int, str]:
    """Orden numérico de QIDs (Q90 < Q1234) para elegir de forma determinista."""
    return (int(qid[1:]), qid) if qid[1:].isdigit() else (1 << 62, qid)


def fetch_core(client: WikidataClient, qids: list[str]) -> dict[str, dict]:
    query = f"""
SELECT ?item ?labelEn ?labelEs ?labelMul ?descEn ?descEs ?sitelinks ?enwiki ?eswiki WHERE {{
  VALUES ?item {{ {_values(qids)} }}
  OPTIONAL {{ ?item rdfs:label ?labelEn FILTER(LANG(?labelEn) = "en") }}
  OPTIONAL {{ ?item rdfs:label ?labelEs FILTER(LANG(?labelEs) = "es") }}
  OPTIONAL {{ ?item rdfs:label ?labelMul FILTER(LANG(?labelMul) = "mul") }}
  OPTIONAL {{ ?item schema:description ?descEn FILTER(LANG(?descEn) = "en") }}
  OPTIONAL {{ ?item schema:description ?descEs FILTER(LANG(?descEs) = "es") }}
  OPTIONAL {{ ?item wikibase:sitelinks ?sitelinks }}
  OPTIONAL {{ ?enwiki schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> }}
  OPTIONAL {{ ?eswiki schema:about ?item ; schema:isPartOf <https://es.wikipedia.org/> }}
}}"""
    out = {}
    for r in client.sparql(query):
        v = {k: b["value"] for k, b in r.items()}
        out[_qid(v["item"])] = v
    return out


def fetch_statements(client: WikidataClient, qids: list[str]) -> list[dict]:
    props = " ".join(f'("{p}" p:{p} ps:{p})' for p in [*SINGLE, *EXTERNAL_IDS, *MULTI])
    query = f"""
SELECT ?item ?pid ?val ?rank ?labelEn ?labelEs ?labelMul WHERE {{
  VALUES ?item {{ {_values(qids)} }}
  VALUES (?pid ?p ?ps) {{ {props} }}
  ?item ?p ?st . ?st ?ps ?val ; wikibase:rank ?rank .
  OPTIONAL {{ ?val rdfs:label ?labelEn FILTER(LANG(?labelEn) = "en") }}
  OPTIONAL {{ ?val rdfs:label ?labelEs FILTER(LANG(?labelEs) = "es") }}
  OPTIONAL {{ ?val rdfs:label ?labelMul FILTER(LANG(?labelMul) = "mul") }}
}}"""
    rows = []
    for r in client.sparql(query):
        val = r["val"]
        is_entity = val["type"] == "uri" and "/entity/Q" in val["value"]
        rows.append({
            "qid": _qid(r["item"]["value"]),
            "pid": r["pid"]["value"],
            "rank": r["rank"]["value"].replace(RANK_URI, ""),
            "value": _qid(val["value"]) if is_entity else val["value"],
            "lang": val.get("xml:lang"),
            "label": (r.get("labelEn") or r.get("labelMul") or r.get("labelEs") or {}).get("value"),
            "is_entity": is_entity,
        })
    return rows


def fetch_aliases(client: WikidataClient, qids: list[str]) -> list[tuple[str, str, str]]:
    query = f"""
SELECT ?item ?alias WHERE {{
  VALUES ?item {{ {_values(qids)} }}
  ?item skos:altLabel ?alias FILTER(LANG(?alias) IN ("en", "es", "mul"))
}}"""
    return [(_qid(r["item"]["value"]), r["alias"]["value"], r["alias"]["xml:lang"])
            for r in client.sparql(query)]


def best_rank(items: list[dict], rank_key=lambda x: x["rank"]) -> list[dict]:
    live = [i for i in items if rank_key(i) != "DeprecatedRank"]
    preferred = [i for i in live if rank_key(i) == "PreferredRank"]
    return preferred or live


def count_references(claim: dict) -> int:
    """Nº de referencias, sin contar 'imported from Wikimedia project' (P143),
    que solo indica de qué Wikipedia se copió el dato, no una fuente."""
    return sum(1 for r in claim.get("references", []) if set(r.get("snaks", {})) != {"P143"})


def pick_date(claims: list[dict]) -> tuple[dict | None, bool]:
    """Devuelve (fecha elegida, hay_conflicto)."""
    parsed = []
    for c in claims:
        snak = c.get("mainsnak", {})
        if snak.get("snaktype") != "value":
            continue  # 'somevalue' (desconocido) o 'novalue'
        v = snak["datavalue"]["value"]
        date, year = parse_wikidata_time(v["time"], v["precision"])
        parsed.append({
            "rank": {"preferred": "PreferredRank", "deprecated": "DeprecatedRank"}.get(
                c.get("rank"), "NormalRank"),
            "date": date, "year": year, "precision_num": v["precision"],
            "precision": PRECISION_NAMES.get(v["precision"], str(v["precision"])),
            "calendar": CALENDARS.get(v["calendarmodel"], v["calendarmodel"]),
            "refs": count_references(c),
        })
    best = best_rank(parsed)
    if not best:
        return None, False
    # Desempate: más precisa > más referencias > orden del API (max conserva el primero).
    chosen = max(best, key=lambda d: (d["precision_num"], d["refs"]))
    conflict = len({d["year"] for d in best}) > 1
    return chosen, conflict


def apply_corrections(conn: sqlite3.Connection, path: Path) -> None:
    """Aplica data/corrections.csv: correcciones manuales a datos de Wikidata.

    Cada fila es (qid, field, value, reason). `field` es una columna de
    `authors` o `remove_name` (borra un nombre de `author_names`). El valor
    original se guarda en `author_corrections` para que la corrección sea trazable.
    """
    if not path.exists():
        return
    author_cols = {r[1] for r in conn.execute("PRAGMA table_info(authors)")} - {"qid"}
    with open(path, encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["qid"].strip()]
    for r in rows:
        qid, field, value = r["qid"].strip(), r["field"].strip(), r["value"]
        if field == "remove_name":
            found = conn.execute("SELECT COUNT(*) FROM author_names WHERE qid = ? AND name = ?",
                                 (qid, value)).fetchone()[0]
            conn.execute("DELETE FROM author_names WHERE qid = ? AND name = ?", (qid, value))
            original, value = (value if found else None), None
        elif field in author_cols:
            row = conn.execute(f"SELECT {field} FROM authors WHERE qid = ?", (qid,)).fetchone()
            if row is None:
                raise ValueError(f"corrections.csv: {qid} no está en authors")
            original = row[0]
            conn.execute(f"UPDATE authors SET {field} = ? WHERE qid = ?", (value, qid))
        else:
            raise ValueError(f"corrections.csv: campo no válido '{field}'")
        conn.execute("INSERT INTO author_corrections VALUES (?,?,?,?,?)",
                     (qid, field, original, value, r["reason"]))
    log.info("Aplicadas %d correcciones manuales", len(rows))


NAME_TYPE_PRIORITY = ("pseudonym", "main", "birth_name", "alias")


def classify_name_type(seed_key: str, names: dict[str, set[str]]) -> str:
    """Qué tipo de nombre del autor es el que aparece en el seed.

    `names` agrupa las claves de comparación (match_key) del autor por tipo:
    pseudonym (P742), main (etiquetas), birth_name (P1477), alias.
    Prioridad: un seudónimo se marca como tal aunque sea también la etiqueta
    principal (Mark Twain). Para el nombre de nacimiento basta con que todas
    las palabras del seed estén en él y empiece igual ('Samuel Clemens' ⊂
    'Samuel Langhorne Clemens'); 'Calderón de la Barca' no cuenta frente a
    'Pedro Calderón de la Barca' porque es una forma abreviada, no el nombre real.
    """
    seed_tokens = seed_key.split()
    for kind in NAME_TYPE_PRIORITY:
        for name in names.get(kind, ()):
            if seed_key == name:
                return kind
            name_tokens = name.split()
            if (kind == "birth_name" and len(seed_tokens) >= 2
                    and seed_tokens[0] == name_tokens[0] and set(seed_tokens) <= set(name_tokens)):
                return kind
    return "other"


def classify_seed_names(conn: sqlite3.Connection) -> None:
    """Rellena seed_resolution.name_type para las filas con autor."""
    names: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for qid, label, label_es in conn.execute("SELECT qid, label, label_es FROM authors"):
        for lbl in (label, label_es):
            if lbl:
                names[qid]["main"].add(match_key(lbl))
    for qid, name, kind in conn.execute("SELECT qid, name, kind FROM author_names"):
        names[qid][kind].add(match_key(name))
    rows = conn.execute("""SELECT r.seed_id, r.qid, s.match_key FROM seed_resolution r
                           JOIN seed_names s USING (seed_id) WHERE r.qid IS NOT NULL""").fetchall()
    conn.execute("UPDATE seed_resolution SET name_type = NULL")
    conn.executemany("UPDATE seed_resolution SET name_type = ? WHERE seed_id = ?",
                     [(classify_name_type(key, names[qid]), sid) for sid, qid, key in rows])


def run(conn: sqlite3.Connection, client: WikidataClient,
        corrections_path: Path | None = None) -> None:
    qids = sorted({r[0] for r in conn.execute(
        "SELECT DISTINCT qid FROM seed_resolution WHERE qid IS NOT NULL")})
    log.info("Enriqueciendo %d autores", len(qids))
    hits0, misses0 = client.hits, client.misses

    core, statements, aliases = {}, [], []
    for i in range(0, len(qids), BATCH):
        chunk = qids[i:i + BATCH]
        batch_core = fetch_core(client, chunk)
        for v in batch_core.values():
            v["retrieved_at"] = client.last_retrieved_at  # fecha de la descarga, no de la ejecución
        core.update(batch_core)
        statements += fetch_statements(client, chunk)
        aliases += fetch_aliases(client, chunk)

    by_author: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for s in statements:
        by_author[s["qid"]][s["pid"]].append(s)

    with conn:
        for table in ("author_corrections", "author_occupations", "author_citizenships",
                      "author_languages", "author_names", "authors"):
            conn.execute(f"DELETE FROM {table}")

        for n, qid in enumerate(qids, 1):
            c = core.get(qid, {})
            props = by_author.get(qid, {})
            row = {
                "qid": qid,
                # 'mul' = etiqueta válida para todos los idiomas (Wikidata, 2024+).
                "label": c.get("labelEn") or c.get("labelMul") or c.get("labelEs"),
                "label_es": c.get("labelEs") or c.get("labelMul"),
                "description": c.get("descEn") or c.get("descEs"),
                "sitelinks": int(c["sitelinks"]) if "sitelinks" in c else None,
                "wikipedia_en": c.get("enwiki"),
                "wikipedia_es": c.get("eswiki"),
                "retrieved_at": c.get("retrieved_at"),
            }
            conflicts = []

            for pid, field in SINGLE.items():
                vals = sorted(best_rank(props.get(pid, [])), key=lambda v: _qnum(v["value"]))
                if len({v["value"] for v in vals}) > 1:
                    conflicts.append(field)
                first = vals[0] if vals else None
                if field != "gender":
                    row[f"{field}_qid"] = first["value"] if first else None
                row[field] = first["label"] if first else None

            for pid, field in EXTERNAL_IDS.items():
                ids = sorted({v["value"] for v in best_rank(props.get(pid, []))})
                row[field] = " | ".join(ids) or None

            for kind, pid in (("birth", "P569"), ("death", "P570")):
                date, conflict = pick_date(client.get_claims(qid, pid))
                if conflict:
                    conflicts.append(f"{kind}_date")
                for k in ("date", "year", "precision", "calendar"):
                    row[f"{kind}_{k}"] = date[k] if date else None
            row["conflicting_fields"] = ",".join(conflicts) or None

            cols = ",".join(row)
            conn.execute(f"INSERT INTO authors ({cols}) VALUES ({','.join('?' * len(row))})",
                         list(row.values()))

            for pid, table, col in (("P106", "author_occupations", "occupation"),
                                    ("P27", "author_citizenships", "country"),
                                    ("P1412", "author_languages", "language")):
                for v in best_rank(props.get(pid, [])):
                    if v["is_entity"]:
                        conn.execute(
                            f"INSERT OR IGNORE INTO {table} VALUES (?,?,?)",
                            (qid, v["value"], v["label"]))
            for pid, kind in (("P742", "pseudonym"), ("P1477", "birth_name")):
                for v in best_rank(props.get(pid, [])):
                    conn.execute("INSERT OR IGNORE INTO author_names VALUES (?,?,?,?)",
                                 (qid, v["value"], kind, v["lang"]))
            if n % 100 == 0:
                log.info("Enriquecidos %d/%d", n, len(qids))

        conn.executemany("INSERT OR IGNORE INTO author_names VALUES (?,?,'alias',?)", aliases)
        if corrections_path is not None:
            apply_corrections(conn, corrections_path)
        classify_seed_names(conn)  # después de las correcciones: dependen de las etiquetas

    log.info("Enriquecimiento: %d peticiones desde caché, %d nuevas", client.hits - hits0, client.misses - misses0)
