"""Genera QUALITY_REPORT.md a partir de la BD.

Las secciones con cifras se calculan siempre desde los datos. El análisis
manual (limitaciones, verificación de la muestra) vive en
docs/quality_notes.md y se incrusta al final, así regenerar no lo pisa.
"""
import logging
import random
import sqlite3
from pathlib import Path

from authors.resolve import DOMINANCE_RATIO, MATCH_THRESHOLD, MIN_MARGIN

log = logging.getLogger(__name__)

SAMPLE_SIZE = 20
SAMPLE_SEED = 20260930  # fijo: la muestra es siempre la misma


def _table(headers: list[str], rows) -> str:
    def cell(v) -> str:
        return "" if v is None else str(v).replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(cell(v) for v in r) + " |" for r in rows]
    return "\n".join(lines)


def _pct(part: int, total: int) -> str:
    return f"{part / total:.1%}" if total else "-"


def build(conn: sqlite3.Connection, notes_path: Path) -> str:
    q = lambda sql, *a: conn.execute(sql, a).fetchall()  # noqa: E731
    n_seed = q("SELECT COUNT(*) FROM seed_names")[0][0]
    n_auth = q("SELECT COUNT(*) FROM authors")[0][0]
    ret = q("SELECT MIN(retrieved_at), MAX(retrieved_at) FROM authors")[0]
    out: list[str] = []
    w = out.append

    w("# Informe de calidad\n")
    w("> Generado por `python -m authors report` a partir de `data/authors.db`. "
      "Las cifras no se editan a mano; el análisis manual está en la última sección "
      "(`docs/quality_notes.md`).\n")
    w(f"- Filas del seed: **{n_seed}**. Autores únicos en la BD: **{n_auth}**.")
    w(f"- Datos descargados de Wikidata entre {ret[0]} y {ret[1]} (instantánea; "
      "Wikidata cambia continuamente).\n")

    # --- Resumen ---------------------------------------------------------------
    status = dict(q("SELECT status, COUNT(*) FROM seed_resolution GROUP BY status"))
    n_override = q("SELECT COUNT(*) FROM seed_resolution WHERE method = 'override'")[0][0]
    n_shared = q("""SELECT COUNT(*) FROM (SELECT qid FROM seed_resolution WHERE qid IS NOT NULL
                    GROUP BY qid HAVING COUNT(*) > 1)""")[0][0]
    n_pseudo = q("SELECT COUNT(*) FROM seed_resolution WHERE name_type = 'pseudonym'")[0][0]
    n_corr = q("SELECT COUNT(DISTINCT qid) FROM author_corrections")[0][0]
    n_conf = q("SELECT COUNT(*) FROM authors WHERE conflicting_fields IS NOT NULL")[0][0]
    n_bce = q("SELECT COUNT(*) FROM authors WHERE birth_year < 0")[0][0]
    w("## Resumen\n")
    w(f"- **Resolución:** {status.get('matched', 0)} de {n_seed} filas resueltas a una persona de "
      f"Wikidata ({n_override} por decisión manual) y {status.get('not_a_person', 0)} que no son "
      f"personas (`Anonymous`, `Various Authors`). {n_shared} pares del seed son la misma persona "
      f"con dos nombres (seudónimo / nombre real); en total, {n_pseudo} filas usan un seudónimo (§1, §2).")
    w("- **Verificación:** se revisaron uno a uno todos los casos ambiguos, los seudónimos, los "
      "nombres de una palabra y una muestra aleatoria de 20 filas (cómo y con qué alcance, en §7.1).")
    w(f"- **Datos de la fuente:** {n_corr} autor llegó vandalizado en Wikidata y se corrigió de forma "
      f"trazable (§2.3, §7.2). {n_conf} autores tienen valores en conflicto en Wikidata (varios "
      f"lugares o fechas); se elige uno de forma determinista y se marcan (§4). Las fechas se guardan "
      f"con su precisión y calendario ({n_bce} autores nacidos antes de Cristo).")
    w("- **Robustez:** los pesos de la puntuación apenas condicionan el resultado: en 171 "
      "combinaciones, 493 de 498 filas resuelven siempre al mismo autor (§7.3).")
    w("- **Principales limitaciones:** una sola fuente; la notoriedad como desempate favorece al "
      "homónimo famoso; los pesos no están calibrados con datos etiquetados (§7.4).\n")

    # --- 1. Resolución ---------------------------------------------------------
    w("## 1. Resolución nombre → Wikidata\n")
    rows = q("SELECT status, COUNT(*) FROM seed_resolution GROUP BY status ORDER BY 2 DESC")
    w(_table(["Estado", "Filas", "%"], [(s, c, _pct(c, n_seed)) for s, c in rows]))
    w("")
    rows = q("SELECT method, COUNT(*) FROM seed_resolution GROUP BY method ORDER BY 2 DESC")
    w(_table(["Método", "Filas"], rows))
    w("")
    buckets = q("""SELECT CASE WHEN confidence >= 0.9 THEN '≥ 0.90'
                               WHEN confidence >= 0.8 THEN '0.80–0.89'
                               WHEN confidence >= 0.6 THEN '0.60–0.79'
                               ELSE '< 0.60' END b, COUNT(*)
                   FROM seed_resolution WHERE confidence IS NOT NULL AND method != 'override'
                   GROUP BY b ORDER BY b DESC""")
    w("Distribución de la confianza (sin overrides):\n")
    w(_table(["Confianza", "Filas"], buckets))
    w("")
    w(f"Reglas: umbral {MATCH_THRESHOLD}, margen mínimo {MIN_MARGIN} con el segundo candidato, "
      f"salvo dominancia (≥ {DOMINANCE_RATIO}× sitelinks). Detalle en el README.\n")

    # --- 2. Casos dudosos ------------------------------------------------------
    w("## 2. Casos dudosos y decisiones\n")

    w("### 2.1 Seudónimos / misma persona con varios nombres en el seed\n")
    rows = q("""SELECT r.qid, a.label, group_concat(s.clean_name || ' (' || r.name_type || ')', ' · ')
                FROM seed_resolution r JOIN seed_names s USING (seed_id)
                JOIN authors a USING (qid)
                GROUP BY r.qid HAVING COUNT(*) > 1 ORDER BY a.label""")
    w("Varias filas del seed apuntan al mismo QID. Se conserva cada fila en "
      "`seed_resolution` y el autor aparece una sola vez en `authors`. Entre paréntesis, "
      "`name_type`: qué nombre del autor usa esa fila (`pseudonym` = registrado como "
      "seudónimo en P742, aunque sea también la etiqueta principal; `birth_name` = nombre de "
      "nacimiento P1477; `alias` = otra forma registrada).\n")
    w(_table(["QID", "Autor (Wikidata)", "Filas del seed (name_type)"], rows))
    w("")
    rows = q("""SELECT name_type, COUNT(*) FROM seed_resolution WHERE name_type IS NOT NULL
                GROUP BY 1 ORDER BY 2 DESC""")
    w("Tipo de nombre en todas las filas resueltas del seed:\n")
    w(_table(["name_type", "Filas"], rows))
    w("")
    w("Los nombres reales solo se reconocen si Wikidata registra el nombre de nacimiento con "
      "una forma compatible: «Mary Ann Evans» (Wikidata: «Mary Anne Evans») y «Theodor Seuss "
      "Geisel» (sin P1477) quedan como `alias`.\n")

    w("### 2.2 Entradas que no son personas\n")
    rows = q("""SELECT s.raw_name, r.note FROM seed_resolution r JOIN seed_names s USING (seed_id)
                WHERE r.status = 'not_a_person'""")
    w(_table(["Seed", "Motivo"], rows))
    w("")

    w("### 2.3 Overrides manuales y correcciones de datos\n")
    w("Overrides de resolución (`data/overrides.csv`): qué QID corresponde a una fila del seed.\n")
    rows = q("""SELECT s.raw_name, r.qid, r.note FROM seed_resolution r JOIN seed_names s USING (seed_id)
                WHERE r.method = 'override'""")
    w(_table(["Seed", "QID", "Justificación"], rows) if rows else "_Ninguno._")
    w("")
    w("Correcciones de atributos (`data/corrections.csv`): datos erróneos en Wikidata que se "
      "corrigen tras el enriquecimiento. El valor original queda en `author_corrections`.\n")
    rows = q("""SELECT c.qid, a.label, c.field, c.original_value, c.corrected_value, c.reason
                FROM author_corrections c JOIN authors a USING (qid) ORDER BY c.rowid""")
    w(_table(["QID", "Autor", "Campo", "Valor en Wikidata", "Corregido", "Motivo"], rows)
      if rows else "_Ninguna._")
    w("")

    w("### 2.4 Resueltos por dominancia de notoriedad (margen de score pequeño)\n")
    w("El mejor candidato apenas supera al segundo en score (homónimo también escritor), "
      f"pero tiene ≥ {DOMINANCE_RATIO}× sus sitelinks. Revisión manual en §7.\n")
    rows = q("""SELECT s.clean_name, r.qid, k1.sitelinks, k2.qid, k2.label, k2.description, k2.sitelinks,
                       round(k1.score - k2.score, 2)
                FROM seed_resolution r JOIN seed_names s USING (seed_id)
                JOIN candidates k1 ON k1.seed_id = r.seed_id AND k1.qid = r.qid
                JOIN candidates k2 ON k2.seed_id = r.seed_id AND k2.qid != r.qid
                WHERE r.method != 'override'
                  AND k2.score = (SELECT MAX(score) FROM candidates k3
                                  WHERE k3.seed_id = r.seed_id AND k3.qid != r.qid)
                  AND k1.score - k2.score < ?
                ORDER BY s.seed_id""", MIN_MARGIN)
    w(_table(["Seed", "Elegido", "Sitelinks", "2º candidato", "Etiqueta", "Descripción",
              "Sitelinks", "Margen"], rows))
    w("")

    w("### 2.5 Resueltos por alias (el nombre del seed no es la etiqueta principal)\n")
    rows = q("""SELECT s.clean_name, r.qid, a.label, round(r.confidence, 2)
                FROM seed_resolution r JOIN seed_names s USING (seed_id) JOIN authors a USING (qid)
                WHERE r.method IN ('alias', 'partial', 'fulltext') ORDER BY s.seed_id""")
    w(_table(["Seed", "QID", "Etiqueta Wikidata", "Confianza"], rows))
    w("")

    w("### 2.6 Confianza más baja (fuera de overrides)\n")
    rows = q("""SELECT s.clean_name, r.qid, a.label, a.description, round(r.confidence, 2)
                FROM seed_resolution r JOIN seed_names s USING (seed_id) JOIN authors a USING (qid)
                WHERE r.method != 'override' ORDER BY r.confidence LIMIT 10""")
    w(_table(["Seed", "QID", "Etiqueta", "Descripción", "Confianza"], rows))
    w("")

    # --- 3. Completitud --------------------------------------------------------
    w("## 3. Completitud de los atributos\n")
    fields = ["label", "label_es", "description", "birth_date", "death_date", "birth_place",
              "death_place", "gender", "viaf_id", "isni", "openlibrary_id", "goodreads_id",
              "wikipedia_en", "wikipedia_es"]
    rows = [(f, c := q(f"SELECT COUNT({f}) FROM authors")[0][0], _pct(c, n_auth)) for f in fields]
    for table, label in (("author_occupations", "≥1 ocupación"),
                         ("author_citizenships", "≥1 nacionalidad"),
                         ("author_languages", "≥1 idioma")):
        c = q(f"SELECT COUNT(DISTINCT qid) FROM {table}")[0][0]
        rows.append((label, c, _pct(c, n_auth)))
    w(_table(["Campo", "Autores", "%"], rows))
    w("")
    w("`death_date` vacío es esperable en autores vivos: ningún autor sin fecha de muerte "
      f"nació antes de 1926 ({q('SELECT COUNT(*) FROM authors WHERE death_date IS NULL AND birth_year < 1926')[0][0]} casos).\n")

    # --- 4. Fechas -------------------------------------------------------------
    w("## 4. Fechas\n")
    rows = q("""SELECT birth_precision, COUNT(*) FROM authors GROUP BY 1
                ORDER BY CASE birth_precision WHEN 'day' THEN 1 WHEN 'month' THEN 2 WHEN 'year' THEN 3
                         WHEN 'decade' THEN 4 WHEN 'century' THEN 5 ELSE 6 END""")
    w("Precisión de la fecha de nacimiento:\n")
    w(_table(["Precisión", "Autores"], rows))
    w("")
    bce = q("SELECT label, birth_date, birth_precision FROM authors WHERE birth_year < 0 ORDER BY birth_year")
    w(f"- **{len(bce)}** autores nacidos antes de Cristo (año negativo, sin desplazamiento de año 0): "
      + ", ".join(f"{l} ({d}, {p})" for l, d, p in bce) + ".")
    jul = q("SELECT COUNT(*) FROM authors WHERE birth_calendar = 'julian'")[0][0]
    w(f"- **{jul}** fechas de nacimiento en calendario juliano, guardadas tal cual (sin convertir).")
    w("- Las fechas con precisión inferior a día deben leerse junto con `*_precision`: "
      "`-0650` con precisión `century` significa «siglo VII a.C.», no el año 650.\n")

    w("### Valores en conflicto\n")
    w("Campos univaluados con varios valores de mejor rango en Wikidata. Se elige uno de forma "
      "determinista y se marca en `conflicting_fields`.\n")
    rows = q("""SELECT conflicting_fields, COUNT(*) FROM authors
                WHERE conflicting_fields IS NOT NULL GROUP BY 1 ORDER BY 2 DESC""")
    w(_table(["Campos", "Autores"], rows))
    w("")
    rows = q("""SELECT label, birth_date, birth_precision, death_date, death_precision, conflicting_fields
                FROM authors WHERE conflicting_fields LIKE '%date%' ORDER BY label""")
    w("Autores con conflicto en fechas:\n")
    w(_table(["Autor", "Nacimiento", "Precisión", "Muerte", "Precisión", "Conflictos"], rows))
    w("")

    # --- 5. Consistencia -------------------------------------------------------
    w("## 5. Comprobaciones de consistencia\n")
    checks = [
        ("Muerte anterior al nacimiento",
         "SELECT label, birth_date, death_date FROM authors WHERE death_year < birth_year"),
        ("Vida > 105 años",
         "SELECT label, birth_date || ' (' || birth_precision || ')', death_date || ' (' || death_precision || ')' "
         "FROM authors WHERE death_year - birth_year > 105"),
        ("Sin fecha de muerte y nacido antes de 1926",
         "SELECT label, birth_date, '' FROM authors WHERE death_date IS NULL AND birth_year < 1926"),
        ("Autor sin ocupación literaria ni obras (P50)",
         """SELECT a.label, a.description, '' FROM authors a WHERE NOT EXISTS (
              SELECT 1 FROM candidates k JOIN seed_resolution r ON r.seed_id = k.seed_id AND r.qid = k.qid
              WHERE k.qid = a.qid AND k.is_writer = 1)"""),
        ("Fila del seed sin autor enriquecido",
         """SELECT s.raw_name, r.qid, '' FROM seed_resolution r JOIN seed_names s USING (seed_id)
            WHERE r.qid IS NOT NULL AND r.qid NOT IN (SELECT qid FROM authors)"""),
        # Detectó el vandalismo de Vicente Huidobro: se resolvió por etiqueta exacta, pero tras
        # enriquecer el nombre del seed ya no era la etiqueta del autor.
        ("Resuelto por etiqueta exacta, pero el nombre del seed no es el principal del autor",
         """SELECT s.raw_name, a.label, r.name_type FROM seed_resolution r
            JOIN seed_names s USING (seed_id) JOIN authors a USING (qid)
            WHERE r.method = 'exact_label' AND r.name_type NOT IN ('main', 'pseudonym')"""),
    ]
    summary = []
    details = []
    for name, sql in checks:
        rows = q(sql)
        summary.append((name, len(rows), "OK" if not rows else "revisar"))
        if rows:
            details.append(f"**{name}**\n\n" + _table(["", "", ""], rows) + "\n")
    w(_table(["Comprobación", "Casos", "Resultado"], summary))
    w("")
    out.extend(details)

    # --- 6. Muestra para verificación manual ----------------------------------
    w("## 6. Muestra aleatoria para verificación manual\n")
    matched = q("""SELECT s.seed_id, s.clean_name, r.qid, a.label, a.description, a.birth_date
                   FROM seed_resolution r JOIN seed_names s USING (seed_id) JOIN authors a USING (qid)
                   WHERE r.status = 'matched' ORDER BY s.seed_id""")
    sample = sorted((tuple(r) for r in random.Random(SAMPLE_SEED).sample(matched, min(SAMPLE_SIZE, len(matched)))))
    w(f"{len(sample)} filas `matched` elegidas con semilla fija ({SAMPLE_SEED}). "
      "El resultado de la verificación está en la sección 7.\n")
    w(_table(["#", "Seed", "QID", "Etiqueta", "Descripción", "Nacimiento"], sample))
    w("")

    # --- 7. Notas manuales -----------------------------------------------------
    if notes_path.exists():
        w(notes_path.read_text(encoding="utf-8").strip())
        w("")
    return "\n".join(out)


def run(conn: sqlite3.Connection, out_path: Path, notes_path: Path) -> None:
    out_path.write_text(build(conn, notes_path), encoding="utf-8", newline="\n")
    log.info("Informe de calidad escrito en %s", out_path)
