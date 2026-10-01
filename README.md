# prueba-hamelyn: base de datos enriquecida de autores

Pipeline reproducible que toma `authors_seed.csv` (500 nombres), resuelve cada nombre a una entidad de **Wikidata**, descarga sus atributos, los normaliza y los guarda en **SQLite**. También genera exports CSV y un informe de calidad.

| | |
|---|---|
| Filas del seed | 500 → **498 resueltas** (1 por override manual) + 2 que no son personas (`Anonymous`, `Various Authors`) |
| Autores únicos | **491**: 7 pares del seed son la misma persona (seudónimo / nombre real) |
| Atributos | nombres (en/es, alias, seudónimos, nombre de nacimiento), fechas con precisión y calendario, lugares, género, ocupaciones, nacionalidades, idiomas, VIAF, ISNI, OpenLibrary, Goodreads, Wikipedia en/es |
| Entregables | [`data/authors.db`](data/authors.db) · [`data/export/`](data/export) · [`QUALITY_REPORT.md`](QUALITY_REPORT.md) · [`ai-usage/`](ai-usage) |

## Ejecución

Requisitos: Python ≥ 3.11. Única dependencia de ejecución: `requests`.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"     # Linux/macOS: .venv/bin/python
.venv/Scripts/python -m authors run --offline       # reconstruye todo desde data/cache, sin red
.venv/Scripts/python -m pytest                      # 28 tests, incluido el pipeline completo
```

`run --offline` reconstruye la BD, los CSV y el informe **exactamente iguales** a los commiteados, sin conexión (lo comprueba `tests/test_pipeline.py`). Sin `--offline`, las peticiones que no están en caché se descargan de Wikidata.

| Comando | Qué hace |
|---|---|
| `load` | Carga el seed en `seed_names` (idempotente) |
| `resolve` | Nombre → QID: candidatos, puntuación, decisión, overrides |
| `enrich` | QID → atributos |
| `export` | Escribe `data/export/*.csv` |
| `report` | Genera `QUALITY_REPORT.md` |
| `run` | Todo lo anterior, con la BD desde cero (la caché se conserva) |

Opciones: `--offline`, `--prune-cache` (con `run`: borra respuestas de caché no usadas), `--limit N`, `--db`, `--seed`, `--export-dir`, `--report`, `-v`.

## Cómo funciona

```
authors_seed.csv ─load─▶ seed_names
                           │ resolve   wbsearchentities (en+es) ─▶ candidatos
                           │           SPARQL: ¿humano? ¿escritor? ¿obras P50? sitelinks
                           │           puntuación ─▶ decisión ─▶ overrides.csv
                           ▼
                     seed_resolution (fila → QID, estado, método, confianza, nota)
                           │ enrich    SPARQL: etiquetas, lugares, ocupaciones, IDs...
                           │           wbgetclaims: fechas (JSON original)
                           ▼
                        authors + tablas relación ─export─▶ CSV ─report─▶ QUALITY_REPORT.md
```

Todas las peticiones HTTP pasan por `WikidataClient`, que guarda cada respuesta cruda en `data/cache/<tipo>/<sha1>.json` junto con sus parámetros y la fecha de descarga: 996 búsquedas, 982 claims y 42 consultas SPARQL, 24 MB en total.

### Estructura

```
src/authors/
  cli.py        comandos
  db.py         esquema SQLite y vistas
  wikidata.py   cliente HTTP: caché, User-Agent, backoff, modo offline
  normalize.py  normalización de nombres y parseo de fechas de Wikidata
  resolve.py    nombre → QID
  enrich.py     QID → atributos
  export.py     CSV
  report.py     informe de calidad
data/
  authors.db            base de datos resultante
  export/               authors.csv (1 fila/autor), seed_resolution.csv (1 fila/seed)
  overrides.csv         resoluciones manuales (fila del seed → QID) con justificación
  corrections.csv       correcciones manuales de datos erróneos de Wikidata, con evidencia
  cache/                respuestas crudas de Wikidata (reproducibilidad)
docs/quality_notes.md   análisis manual, se incrusta en el informe
scripts/sensitivity.py  análisis de sensibilidad de pesos y umbrales (offline)
tests/                  normalización, reglas de resolución, fechas, pipeline completo
ai-usage/               registro del uso de IA
```

### Modelo de datos

| Tabla | Grano | Contenido |
|---|---|---|
| `seed_names` | fila del seed | nombre original, nombre limpio (NFC) y clave de comparación |
| `candidates` | fila × candidato | todos los candidatos evaluados, con sus señales y su score (4.010 filas) |
| `seed_resolution` | fila del seed | QID elegido, `status` (`matched`/`ambiguous`/`no_match`/`not_a_person`), `method`, `confidence`, `note`, `name_type` (qué nombre del autor usa la fila: `pseudonym`/`main`/`birth_name`/`alias`/`other`) |
| `authors` | QID | atributos univaluados; fechas como `birth_date` + `birth_year` + `birth_precision` + `birth_calendar`; `conflicting_fields`; `retrieved_at` |
| `author_occupations`, `author_citizenships`, `author_languages` | autor × valor | QID + etiqueta |
| `author_names` | autor × nombre | `alias`, `pseudonym` (P742), `birth_name` (P1477) |
| `author_corrections` | corrección | correcciones aplicadas desde `corrections.csv`: campo, valor original de Wikidata, valor corregido, motivo |
| `v_authors_flat`, `v_seed_resolution` | vistas | base de los CSV |

`seed_resolution` es la tabla de trazabilidad: por cada fila del seed se puede ver qué se eligió, cómo, con qué confianza y qué otros candidatos hubo (`candidates`).

## Decisiones técnicas

**Wikidata como única fuente.** Es estructurada, abierta, tiene identificadores estables (QID) y ya enlaza con VIAF, ISNI, OpenLibrary y Goodreads, así que esos IDs sirven para cruzar con otras fuentes en el futuro. Añadir más fuentes (OpenLibrary, VIAF) multiplicaría los problemas de reconciliación. Con 2-3 horas, preferí una sola fuente bien resuelta y verificable.

**SQLite.** Es un único fichero y no necesita servidor. Las restricciones (`CHECK`, `PRIMARY KEY`, `FOREIGN KEY`) documentan el modelo, y las vistas dan la forma plana para los CSV.

**Resolución y enriquecimiento separados.** La parte difícil y con más riesgo es decidir *quién* es cada nombre. Esa decisión se guarda con todos sus candidatos y señales antes de descargar nada más, para poder auditarla y corregirla (overrides) sin tocar el enriquecimiento.

**Reglas de resolución** (`resolve.py`):
1. **No-personas.** `Anonymous`, `Various Authors` y similares se marcan con una regla, sin consultar la API.
2. **Candidatos.** Se usa `wbsearchentities` en inglés y en español: coincide con etiquetas y alias, y así encuentra seudónimos y formas alternativas. Hay una búsqueda de respaldo de texto completo restringida a humanos, pero con este seed no se activó nunca: todos los nombres tuvieron algún candidato humano.
3. **Filtro obligatorio: ser persona.** Se acepta P31 = Q5 (humano) o Q21070568 (humano cuya existencia se discute). Sin la segunda clase, *Homer* resolvía a Winslow Homer.
4. **Puntuación:** `0,40·nombre + 0,35·perfil literario + 0,25·notoriedad`.
   - **Nombre:** coincidencia exacta con la etiqueta = 1; con un alias = 0,8; parcial = 0,3.
   - **Perfil literario:** ocupación escritor, filósofo o historiador (o subclases vía `P279*`) = 1; tener obras con autor P50 = 0,5.
   - **Notoriedad:** `log10(sitelinks)`, saturada.
5. **Decisión.** El resultado es `matched` si el score es ≥ 0,6, el candidato tiene perfil literario y le saca un margen ≥ 0,15 al segundo. El margen no se exige cuando el mejor candidato tiene ≥ 5× los sitelinks del segundo (*dominancia*). Así se resuelven homónimos menores que también escriben, como el padre de John Milton. Si no se cumple, el resultado es `ambiguous`: se guarda el mejor candidato con su nota y se revisa a mano.
6. **Overrides.** `data/overrides.csv` recoge decisiones humanas con justificación y se aplica al final. Solo hizo falta uno (Mary Beard).

**¿Dependen los resultados de los pesos?** Apenas. `python scripts/sensitivity.py` recalcula la resolución con 171 combinaciones de pesos y con distintos umbrales, márgenes y factores de dominancia: 493 de 498 filas resuelven siempre al mismo autor. Detalle y casos límite en la §7.3 de `QUALITY_REPORT.md`.

**Fechas: del JSON original, no de SPARQL.** El endpoint SPARQL devuelve las fechas en XSD 1.1: los años a.C. llegan desplazados uno (630 a.C. → `-0629`) y las fechas julianas se convierten a gregoriano. Por eso las fechas se leen con `wbgetclaims` y se guardan tal como están en Wikidata, con su precisión y su calendario. `birth_year` es el año histórico (negativo = a.C.). Una fecha con precisión de siglo (`-0650`, `century`) significa «siglo VII a.C.».

**Varios valores por propiedad.** Se sigue la semántica *best rank* de Wikidata: se ignoran los valores deprecated y, si hay alguno preferred, solo cuentan esos. En los campos de un solo valor, los empates se resuelven de forma determinista:
- **Fechas:** gana la más precisa; después, la que tiene más referencias (sin contar P143, «importado de Wikipedia»).
- **Lugares:** gana el de menor QID.

Cuando hay empate, el campo se marca en `conflicting_fields` (43 autores). Los IDs externos (VIAF, ISNI…) pueden tener varios valores legítimamente, así que se guardan todos, separados por ` | `.

**Reproducibilidad.**
- La caché cruda está commiteada y hay un modo `--offline`.
- `retrieved_at` es la fecha de descarga del dato, no la de ejecución.
- La muestra del informe usa una semilla fija.
- Los CSV usan finales de línea LF, fijados también con `.gitattributes`.

**Buen uso de la API.**
- User-Agent identificable.
- Peticiones secuenciales con pausa entre ellas.
- Backoff exponencial ante 429 y 5xx, que además ralentiza las peticiones siguientes.
- Consultas SPARQL por lotes (100-150 QIDs).
- No se usa `maxlag`: es para bots que editan, y con él las lecturas fallaban cuando la replicación de Wikidata iba con retraso.

## Calidad, limitaciones y casos dudosos

Ver [`QUALITY_REPORT.md`](QUALITY_REPORT.md). Las cifras se generan desde la BD; la §7 es el análisis manual.

**Seudónimos.** Una persona es un único autor (el modelo de Wikidata). Si el seed trae dos nombres de la misma persona (Robert Galbraith / J. K. Rowling), ambas filas apuntan al mismo QID, y `name_type` indica si la fila usa un seudónimo, el nombre principal o el de nacimiento.

**Datos erróneos en la fuente.** Wikidata es editable por cualquiera. Cuando un dato está mal (por ejemplo, vandalismo), no se toca la caché: se añade una fila a `data/corrections.csv` con la evidencia y el pipeline la aplica tras el enriquecimiento, guardando el valor original. Caso real: Vicente Huidobro (§7.2 del informe).

**Cómo añadir un override:** añade una fila a `data/overrides.csv` con `author_name,qid,reason` (deja `qid` vacío para forzar `no_match`) y ejecuta `python -m authors run --offline`. Si el QID es nuevo, hace falta ejecutar sin `--offline` para descargar sus datos.

## Uso de IA

Desarrollado con Claude Code como asistente. En [`ai-usage/`](ai-usage) hay un resumen por sesión: los prompts, qué hizo la IA, qué se validó y cómo, los errores detectados (incluidos los de la propia IA) y qué decisiones tomó el candidato.
