# Informe de calidad

> Generado por `python -m authors report` a partir de `data/authors.db`. Las cifras no se editan a mano; el análisis manual está en la última sección (`docs/quality_notes.md`).

- Filas del seed: **500**. Autores únicos en la BD: **491**.
- Datos descargados de Wikidata entre 2026-09-30T15:46:53Z y 2026-09-30T15:47:23Z (instantánea; Wikidata cambia continuamente).

## Resumen

- **Resolución:** 498 de 500 filas resueltas a una persona de Wikidata (1 por decisión manual) y 2 que no son personas (`Anonymous`, `Various Authors`). 7 pares del seed son la misma persona con dos nombres (seudónimo / nombre real); en total, 42 filas usan un seudónimo (§1, §2).
- **Verificación:** se revisaron uno a uno todos los casos ambiguos, los seudónimos, los nombres de una palabra y una muestra aleatoria de 20 filas (cómo y con qué alcance, en §7.1).
- **Datos de la fuente:** 1 autor llegó vandalizado en Wikidata y se corrigió de forma trazable (§2.3, §7.2). 43 autores tienen valores en conflicto en Wikidata (varios lugares o fechas); se elige uno de forma determinista y se marcan (§4). Las fechas se guardan con su precisión y calendario (16 autores nacidos antes de Cristo).
- **Robustez:** los pesos de la puntuación apenas condicionan el resultado: en 171 combinaciones, 493 de 498 filas resuelven siempre al mismo autor (§7.3).
- **Principales limitaciones:** una sola fuente; la notoriedad como desempate favorece al homónimo famoso; los pesos no están calibrados con datos etiquetados (§7.4).

## 1. Resolución nombre → Wikidata

| Estado | Filas | % |
|---|---|---|
| matched | 498 | 99.6% |
| not_a_person | 2 | 0.4% |

| Método | Filas |
|---|---|
| exact_label | 478 |
| alias | 19 |
| rule | 2 |
| override | 1 |

Distribución de la confianza (sin overrides):

| Confianza | Filas |
|---|---|
| ≥ 0.90 | 411 |
| 0.80–0.89 | 83 |
| 0.60–0.79 | 3 |

Reglas: umbral 0.6, margen mínimo 0.15 con el segundo candidato, salvo dominancia (≥ 5× sitelinks). Detalle en el README.

## 2. Casos dudosos y decisiones

### 2.1 Seudónimos / misma persona con varios nombres en el seed

Varias filas del seed apuntan al mismo QID. Se conserva cada fila en `seed_resolution` y el autor aparece una sola vez en `authors`. Entre paréntesis, `name_type`: qué nombre del autor usa esa fila (`pseudonym` = registrado como seudónimo en P742, aunque sea también la etiqueta principal; `birth_name` = nombre de nacimiento P1477; `alias` = otra forma registrada).

| QID | Autor (Wikidata) | Filas del seed (name_type) |
|---|---|---|
| Q298685 | Dr. Seuss | Dr. Seuss (pseudonym) · Theodor Seuss Geisel (alias) |
| Q131333 | George Eliot | George Eliot (pseudonym) · Mary Ann Evans (alias) |
| Q34660 | J. K. Rowling | J. K. Rowling (main) · Robert Galbraith (pseudonym) |
| Q182804 | Karen Blixen | Karen Blixen (main) · Isak Dinesen (pseudonym) |
| Q38082 | Lewis Carroll | Lewis Carroll (pseudonym) · Charles Lutwidge Dodgson (birth_name) |
| Q7245 | Mark Twain | Mark Twain (pseudonym) · Samuel Clemens (birth_name) |
| Q157322 | Romain Gary | Romain Gary (pseudonym) · Émile Ajar (pseudonym) |

Tipo de nombre en todas las filas resueltas del seed:

| name_type | Filas |
|---|---|
| main | 439 |
| pseudonym | 42 |
| alias | 11 |
| birth_name | 4 |
| other | 2 |

Los nombres reales solo se reconocen si Wikidata registra el nombre de nacimiento con una forma compatible: «Mary Ann Evans» (Wikidata: «Mary Anne Evans») y «Theodor Seuss Geisel» (sin P1477) quedan como `alias`.

### 2.2 Entradas que no son personas

| Seed | Motivo |
|---|---|
| Anonymous | nombre genérico, no es una persona |
| Various Authors | nombre genérico, no es una persona |

### 2.3 Overrides manuales y correcciones de datos

Overrides de resolución (`data/overrides.csv`): qué QID corresponde a una fila del seed.

| Seed | QID | Justificación |
|---|---|---|
| Mary Beard | Q458403 | override manual: Clasicista británica, autora de SPQR (38 sitelinks). Alternativa descartada: Mary Ritter Beard, Q6780609, historiadora estadounidense (28 sitelinks). El seed la agrupa con divulgación contemporánea (Harari, Diamond) |

Correcciones de atributos (`data/corrections.csv`): datos erróneos en Wikidata que se corrigen tras el enriquecimiento. El valor original queda en `author_corrections`.

| QID | Autor | Campo | Valor en Wikidata | Corregido | Motivo |
|---|---|---|---|---|---|
| Q117018 | Vicente Huidobro | label | Vicente Hohoneo | Vicente Huidobro | Vandalismo en Wikidata: la revisión 2532105531 (2026-08-16, cuenta anónima temporal) cambió las etiquetas en/es a «Vicente Hohoneo». Se restaura el valor anterior, que coincide con la etiqueta mul |
| Q117018 | Vicente Huidobro | label_es | Vicente Hohoneo | Vicente Huidobro | Misma edición vandálica (revisión 2532105531) |
| Q117018 | Vicente Huidobro | description | colombian poet | Chilean poet | Misma edición: cambió «Chilean poet» por «colombian poet». Huidobro era chileno (nacido en Santiago, fallecido en Cartagena, Chile) |
| Q117018 | Vicente Huidobro | remove_name | Vicente Hohoneo de la cruz |  | Alias añadido por la edición vandálica (revisión 2532105531) |
| Q117018 | Vicente Huidobro | remove_name | Vicente Hohoneo de la cruz Fernandez |  | Alias añadido por la edición vandálica (revisión 2532105531) |

### 2.4 Resueltos por dominancia de notoriedad (margen de score pequeño)

El mejor candidato apenas supera al segundo en score (homónimo también escritor), pero tiene ≥ 5× sus sitelinks. Revisión manual en §7.

| Seed | Elegido | Sitelinks | 2º candidato | Etiqueta | Descripción | Sitelinks | Margen |
|---|---|---|---|---|---|---|---|
| Mario Benedetti | Q16285 | 46 | Q3848323 | Mario Benedetti | Italian poet and teacher (1955-2020) | 2 | 0.12 |
| Robert Galbraith | Q34660 | 181 | Q7344653 | Robert Galbraith | Scottish Lord of Session | 2 | 0.1 |
| John Milton | Q79759 | 155 | Q3809493 | John Milton | Father of poet John Milton and English composer (1563-1647) | 5 | 0.14 |
| Samuel Johnson | Q183266 | 134 | Q2791832 | Samuel Johnson | President of Columbia University (1696-1772) | 11 | 0.11 |
| Robert Browning | Q233265 | 98 | Q504999 | Robert Browning | Scottish Byzantinist and university professor (1914–1997) | 10 | 0.1 |
| Henry James | Q170509 | 100 | Q5723817 | Henry James | American biographer (1879–1947) | 3 | 0.14 |
| W. B. Yeats | Q40213 | 154 | Q5548182 | Georgie Hyde-Lees | esposa de William Butler Yeats | 5 | 0.14 |
| James Baldwin | Q273210 | 81 | Q15976232 | James Baldwin | American editor and author (1841-1925) | 4 | 0.12 |
| Bruno Schulz | Q148886 | 57 | Q993768 | Bruno Schulz | German architectural historian (1865–1932) | 5 | 0.1 |
| Primo Levi | Q153670 | 92 | Q18606682 | Primo Levi | journalist from Italy (1853-1917) | 4 | 0.13 |
| Nguyễn Du | Q313322 | 37 | Q10799084 | Nguyễn Dữ | 16th-century Vietnamese writer | 4 | 0.09 |
| Jane Goodall | Q184746 | 122 | Q6152650 | Jane R. Goodall | escritora australiana | 4 | 0.04 |

### 2.5 Resueltos por alias (el nombre del seed no es la etiqueta principal)

| Seed | QID | Etiqueta Wikidata | Confianza |
|---|---|---|---|
| João Guimarães Rosa | Q13012 | Guimarães Rosa | 0.83 |
| Eça de Queirós | Q316327 | José Maria de Eça de Queirós | 0.84 |
| Luandino Vieira | Q558950 | José Luandino Vieira | 0.8 |
| Calderón de la Barca | Q170800 | Pedro Calderón de la Barca | 0.87 |
| Robert Galbraith | Q34660 | J. K. Rowling | 0.9 |
| Charles Lutwidge Dodgson | Q38082 | Lewis Carroll | 0.89 |
| Samuel Clemens | Q7245 | Mark Twain | 0.91 |
| Mary Ann Evans | Q131333 | George Eliot | 0.88 |
| L. M. Montgomery | Q273034 | Lucy Maud Montgomery | 0.85 |
| W. B. Yeats | Q40213 | William Butler Yeats | 0.89 |
| Fyodor Dostoevsky | Q991 | Fyodor Dostoyevsky | 0.91 |
| Émile Ajar | Q157322 | Romain Gary | 0.85 |
| S. Y. Agnon | Q133042 | Shmuel Yosef Agnon | 0.87 |
| Isak Dinesen | Q182804 | Karen Blixen | 0.87 |
| Kyung-sook Shin | Q384293 | Shin Kyung-sook | 0.82 |
| Tayeb Salih | Q561434 | al-Tayyib Salih | 0.83 |
| Saadi Shirazi | Q170302 | Saadi | 0.88 |
| Forough Farrokhzad | Q464394 | Forugh Farrokhzad | 0.85 |
| Theodor Seuss Geisel | Q298685 | Dr. Seuss | 0.86 |

### 2.6 Confianza más baja (fuera de overrides)

| Seed | QID | Etiqueta | Descripción | Confianza |
|---|---|---|---|---|
| Marjane Satrapi | Q126633 | Marjane Satrapi | Iranian-French graphic novelist, cartoonist, illustrator, film director, and children's book author (1969–2026) | 0.76 |
| Jane Goodall | Q184746 | Jane Goodall | English primatologist and anthropologist (1934–2025) | 0.78 |
| Luandino Vieira | Q558950 | José Luandino Vieira | Angolan writer | 0.8 |
| Shamini Flint | Q7487568 | Shamini Flint | author based in Singapore | 0.81 |
| Kyung-sook Shin | Q384293 | Shin Kyung-sook | South Korean writer | 0.82 |
| Tayeb Salih | Q561434 | al-Tayyib Salih | Sudanese novelist and short story writer (1929–2009) | 0.83 |
| João Guimarães Rosa | Q13012 | Guimarães Rosa | Brazilian novelist (1908-1967) | 0.83 |
| Miguel Syjuco | Q1768256 | Miguel Syjuco | Filipino writer | 0.84 |
| Eça de Queirós | Q316327 | José Maria de Eça de Queirós | Portuguese writer and diplomat (1845–1900) | 0.84 |
| Forough Farrokhzad | Q464394 | Forugh Farrokhzad | Iranian poet (1935-1967) | 0.85 |

## 3. Completitud de los atributos

| Campo | Autores | % |
|---|---|---|
| label | 491 | 100.0% |
| label_es | 491 | 100.0% |
| description | 491 | 100.0% |
| birth_date | 491 | 100.0% |
| death_date | 356 | 72.5% |
| birth_place | 490 | 99.8% |
| death_place | 353 | 71.9% |
| gender | 491 | 100.0% |
| viaf_id | 491 | 100.0% |
| isni | 491 | 100.0% |
| openlibrary_id | 478 | 97.4% |
| goodreads_id | 434 | 88.4% |
| wikipedia_en | 491 | 100.0% |
| wikipedia_es | 483 | 98.4% |
| ≥1 ocupación | 491 | 100.0% |
| ≥1 nacionalidad | 488 | 99.4% |
| ≥1 idioma | 490 | 99.8% |

`death_date` vacío es esperable en autores vivos: ningún autor sin fecha de muerte nació antes de 1926 (0 casos).

## 4. Fechas

Precisión de la fecha de nacimiento:

| Precisión | Autores |
|---|---|
| day | 461 |
| month | 2 |
| year | 19 |
| decade | 6 |
| century | 3 |

- **16** autores nacidos antes de Cristo (año negativo, sin desplazamiento de año 0): Homer (-0900, century), Sappho (-0650, century), Laozi (-0579, century), Confucius (-0551, year), Sun Tzu (-0544, year), Aeschylus (-0525, year), Sophocles (-0496, year), Herodotus (-0484, year), Euripides (-0480, decade), Thucydides (-0460, decade), Plato (-0428, decade), Aristotle (-0384, year), Virgil (-0070-10-15, day), Horace (-0065-12-08, day), Ovid (-0043-03-20, day), Seneca (-0004, decade).
- **35** fechas de nacimiento en calendario juliano, guardadas tal cual (sin convertir).
- Las fechas con precisión inferior a día deben leerse junto con `*_precision`: `-0650` con precisión `century` significa «siglo VII a.C.», no el año 650.

### Valores en conflicto

Campos univaluados con varios valores de mejor rango en Wikidata. Se elige uno de forma determinista y se marca en `conflicting_fields`.

| Campos | Autores |
|---|---|
| birth_place | 20 |
| death_place | 11 |
| birth_date | 5 |
| birth_place,death_place | 3 |
| birth_place,birth_date | 2 |
| death_date | 1 |
| birth_date,death_date | 1 |

Autores con conflicto en fechas:

| Autor | Nacimiento | Precisión | Muerte | Precisión | Conflictos |
|---|---|---|---|---|---|
| Bapsi Sidhwa | 1938-08-11 | day | 2024-12-25 | day | birth_date |
| Eileen Chang | 1920-09-30 | day | 1995-09-08 | day | birth_place,birth_date |
| Ismat Chughtai | 1915-08-15 | day | 1991-10-24 | day | birth_date,death_date |
| José Martínez Ruiz | 1873-06-08 | day | 1967-03-03 | day | birth_date |
| Lygia Fagundes Telles | 1918-04-19 | day | 2022-04-03 | day | birth_place,birth_date |
| Nâzım Hikmet | 1902-01-15 | day | 1963-06-03 | day | birth_date |
| Rosario Castellanos | 1925-05-25 | day | 1974-08-07 | day | birth_date |
| Sadegh Hedayat | 1903-02-17 | day | 1951-04-09 | day | birth_date |
| Sun Tzu | -0544 | year | -0496 | year | death_date |

## 5. Comprobaciones de consistencia

| Comprobación | Casos | Resultado |
|---|---|---|
| Muerte anterior al nacimiento | 0 | OK |
| Vida > 105 años | 1 | revisar |
| Sin fecha de muerte y nacido antes de 1926 | 0 | OK |
| Autor sin ocupación literaria ni obras (P50) | 0 | OK |
| Fila del seed sin autor enriquecido | 0 | OK |
| Resuelto por etiqueta exacta, pero el nombre del seed no es el principal del autor | 1 | revisar |

**Vida > 105 años**

|  |  |  |
|---|---|---|
| Murasaki Shikibu | 0970 (decade) | 1100 (century) |

**Resuelto por etiqueta exacta, pero el nombre del seed no es el principal del autor**

|  |  |  |
|---|---|---|
| Andrey Platonov | Andrei Platonov | other |

## 6. Muestra aleatoria para verificación manual

20 filas `matched` elegidas con semilla fija (20260930). El resultado de la verificación está en la sección 7.

| # | Seed | QID | Etiqueta | Descripción | Nacimiento |
|---|---|---|---|---|---|
| 12 | Carmen Laforet | Q269123 | Carmen Laforet | Spanish author (1921-2004) | 1921-09-06 |
| 26 | Juan Rulfo | Q200661 | Juan Rulfo | Mexican writer (1917–1986) | 1917-05-16 |
| 114 | Mark Twain | Q7245 | Mark Twain | American author and humorist (1835–1910) | 1835-11-30 |
| 158 | Rudyard Kipling | Q34743 | Rudyard Kipling | English writer and poet (1865–1936) | 1865-12-30 |
| 208 | Chimamanda Ngozi Adichie | Q230141 | Chimamanda Ngozi Adichie | Nigerian writer (born 1977) | 1977-09-15 |
| 215 | Cormac McCarthy | Q272610 | Cormac McCarthy | American novelist, playwright, and screenwriter (1933–2023) | 1933-07-20 |
| 237 | Pierre Corneille | Q747 | Pierre Corneille | French tragedian (1606–1684) | 1606-06-06 |
| 257 | Heinrich Heine | Q44403 | Heinrich Heine | German poet, writer and literary critic (1797–1856) | 1797-12-13 |
| 291 | Luigi Pirandello | Q1403 | Luigi Pirandello | Italian dramatist, novelist, short story writer and poet (1867-1936) | 1867-06-28 |
| 323 | Jo Nesbø | Q202693 | Jo Nesbø | Norwegian novelist, musician and economist | 1960-03-29 |
| 328 | Tove Jansson | Q102071 | Tove Jansson | Finnish children's writer and illustrator (1914–2001) | 1914-08-09 |
| 330 | Halldór Laxness | Q80321 | Halldór Laxness | Icelandic author (1902-1998) | 1902-04-23 |
| 346 | Yasunari Kawabata | Q43736 | Yasunari Kawabata | Japanese novelist (1899–1972) | 1899-06-11 |
| 363 | Mo Yan | Q8998 | Mo Yan | Chinese novelist and screenwriter | 1955-02-17 |
| 365 | Lao She | Q315167 | Lao She | Chinese writer, novelist and playwright (1899-1966) | 1899-02-03 |
| 369 | Can Xue | Q1072531 | Can Xue | Chinese writer, literary critic, and tailor | 1953-05-30 |
| 374 | Rabindranath Tagore | Q7241 | Rabindranath Tagore | Bengali poet, philosopher and polymath (1861–1941) | 1861-05-07 |
| 385 | Ismat Chughtai | Q3080325 | Ismat Chughtai | Indian writer (1911-1991) | 1915-08-15 |
| 421 | Abraham Verghese | Q1446797 | Abraham Verghese | American physician, teacher, novelist | 1955-05-30 |
| 482 | Douglas Adams | Q42 | Douglas Adams | British science fiction writer and humorist (1952–2001) | 1952-03-11 |

## 7. Análisis manual

> Esta sección está escrita a mano (`docs/quality_notes.md`); el resto del informe se genera desde los datos.

### 7.1 Qué se ha revisado y cómo

| Revisión | Alcance | Resultado |
|---|---|---|
| Casos `ambiguous` de la primera ejecución (hoy en §2.3 y §2.4) | 14/14 | 13 correctos (resueltos después con la regla de dominancia) y 1 incorrecto: Homer → Winslow Homer. Se corrigió aceptando Q21070568 («humano cuya existencia se discute») como persona. |
| Nombres de una sola palabra (Homer, Colette, Azorín, Adonis…) | 27/27 | Todos correctos. Azorín resuelve a José Martínez Ruiz (Q443403), Adonis al poeta sirio. |
| Seudónimos / nombres reales del seed | 7 pares | Los 7 resuelven al mismo QID de forma automática (§2.1). |
| Resueltos por alias (§2.5) | todos | Correctos: variantes de transliteración (Dostoevsky/Dostoyevsky, Forough/Forugh), formas cortas (Guimarães Rosa, Eça de Queirós) y seudónimos. |
| Muestra aleatoria (§6) | 20 filas | **20/20 QIDs correctos.** Fechas de nacimiento comparadas con fuentes de referencia: 19/20 coinciden. La que no coincidía era Ismat Chughtai (ver 7.2). |
| Diff entre ejecuciones al cambiar reglas | 500 filas | Cada cambio de reglas se validó comparando la resolución antes y después; solo cambian los casos previstos (ver `ai-usage/`). |
| Reproducibilidad | exports completos | `run --offline` produce CSV idénticos byte a byte a los commiteados (`tests/test_pipeline.py`). |

La revisión de QIDs y fechas la hizo el asistente de IA con conocimiento general, y el candidato la supervisó (ver `ai-usage/`). No es una verificación contra una fuente externa independiente, y así se declara.

### 7.2 Casos dudosos comentados

- **Mary Beard** (único override). Hay dos candidatas con notoriedad parecida: la clasicista británica (38 sitelinks) y la historiadora estadounidense Mary Ritter Beard (28). La regla no decide sola y se resolvió manualmente por contexto: el seed agrupa divulgación contemporánea (Harari, Diamond, Sagan). La justificación queda en `data/overrides.csv`.
- **Ismat Chughtai.** Wikidata tiene 5 fechas de nacimiento de rango normal (1911, 1915 y 1925, con días distintos). El desempate original («la primera que devuelve el API») daba 1911. Se cambió a «más referencias, sin contar P143 (importado de Wikipedia)», y ahora da 1915-08-15. El año coincide con la fuente de referencia (21-08-1915); el día sigue discutido. Queda marcado en `conflicting_fields`. El mismo cambio corrigió la fecha de muerte de Sadegh Hedayat (04-04 → 09-04-1951).
- **Vicente Huidobro: vandalismo en Wikidata.** El QID (Q117018) es correcto, pero la entidad llegó con la etiqueta «Vicente Hohoneo», la descripción «colombian poet» (era chileno) y dos alias inventados. Según el historial, los introdujo una cuenta anónima en la revisión 2532105531 (16-08-2026), y la etiqueta y la descripción inglesas seguían sin revertir al descargar. Se detectó al clasificar el tipo de nombre de cada fila: el nombre del seed ya no coincidía con la etiqueta del autor. Se corrige con `data/corrections.csv`, restaurando los valores anteriores a esa edición; el valor original queda guardado en `author_corrections` (§2.3). La comprobación de §5 «Resuelto por etiqueta exacta, pero el nombre del seed no es el principal del autor» queda para detectar casos parecidos en el futuro. Usar siempre la etiqueta `mul` no era una solución: de los 16 autores en los que difiere de la inglesa, en 15 la inglesa es la correcta (p. ej. Plato frente a «Πλάτων»).
- **Murasaki Shikibu.** Aparece en la comprobación «vida > 105 años» (970–1100), pero es un efecto de la precisión, no un error. El valor preferente de muerte es `1100` con precisión de siglo, es decir, «siglo XI». Por eso las fechas deben leerse siempre junto con `*_precision`.
- **Homero, Laozi, Safo y otros autores antiguos.** Las fechas son aproximaciones con precisión de siglo o década y, en varios casos, con muchos valores alternativos en Wikidata. Se toma el de rango preferente.
- **Robert Galbraith → J. K. Rowling.** Existe en Wikidata una entidad «Robert Galbraith» (juez escocés) con el nombre exacto. Gana Rowling porque el alias coincide, es escritora y tiene 181 sitelinks frente a 2. Es la decisión correcta para una base de datos de autores de libros, pero depende de la regla de notoriedad (ver 7.3).
- **Autores de no ficción y ciencia** (Hawking, Sagan, Goodall, Kahneman…). Se aceptan como autores porque tienen obras con P50 o una ocupación de escritor. Jane Goodall se resuelve a la primatóloga y no a la escritora australiana homónima (Jane R. Goodall, 4 sitelinks).

### 7.3 Sensibilidad de los parámetros

Los pesos de la puntuación (0,40 nombre / 0,35 perfil literario / 0,25 notoriedad) son heurísticos. Para saber si condicionan el resultado, se recalculó la resolución de las 498 filas con otras configuraciones (`python scripts/sensitivity.py`, offline):

- **Repartos razonables** (0,50/0,30/0,20 · 1/3 cada uno · 0,60/0,20/0,20 · 0,30/0,30/0,40): eligen exactamente los mismos 498 autores.
- **Barrido completo** (171 combinaciones en pasos de 0,05): **493 de 498 filas resuelven siempre al mismo autor.** Las 5 restantes:

| Fila | Cuándo cambia | Por qué |
|---|---|---|
| Robert Galbraith | notoriedad ≤ 0,20 | gana el juez escocés homónimo, que tiene el nombre exacto |
| Nguyễn Du | notoriedad ≥ 0,70 | gana Ho Chi Minh, por pura fama |
| Samuel Clemens, Mary Ann Evans | nombre ≥ 0,85 | ganan homónimos desconocidos en lugar del seudónimo famoso |
| **Jane Goodall** | perfil literario claramente por encima de la notoriedad (p. ej. 0,40/0,40/0,20) | **caso límite real**: la primatóloga tiene libros pero no figura como «escritora», y compite con una escritora australiana homónima. Los pesos actuales están cerca de su frontera; hoy se resuelve por dominancia (122 frente a 4 sitelinks) |

- **Umbral** (0,5–0,7), **margen** (0,10–0,20) y **dominancia** (2×–5×) no cambian ninguna decisión en esos rangos. Con valores más estrictos, algunos casos pasan a revisión manual, pero ninguno cambia de autor.

**Por qué el factor de dominancia es 5×.** En las 13 filas donde el mejor candidato saca menos de 0,15 de ventaja al segundo, la proporción de sitelinks entre ambos se reparte en dos grupos muy separados:

| Grupo | Filas | Proporción de sitelinks (elegido / 2º) |
|---|---|---|
| Homónimo claramente menor | Galbraith → Rowling (90×), Henry James (33×), John Milton (31×), W. B. Yeats (31×), Jane Goodall (30×), Mario Benedetti (23×), Primo Levi (23×), James Baldwin (20×), Samuel Johnson (12×), Bruno Schulz (11×), Robert Browning (9,8×), Nguyễn Du (9,2×) | **≥ 9,2×** |
| Ambigüedad real | Mary Beard (38 frente a 28) | **1,4×** |

Cualquier factor entre 1,4× y 9,2× produce exactamente el mismo resultado. Se eligió 5×, que cae en medio de ese hueco. El valor exacto no es una decisión crítica: aunque saliera del rango, ningún autor cambiaría; solo variaría cuántos casos se aceptan automáticamente y cuántos van a revisión manual. El riesgo de la regla es el mismo sesgo de notoriedad descrito en 7.4: si el seed contuviera al homónimo menor, la regla elegiría al famoso sin avisar. Por eso las filas resueltas así se listan en §2.4.

Conclusión: los pesos son una heurística, pero apenas condicionan el resultado. Lo que importa es combinar las tres señales, no el valor exacto de cada peso. Se mantienen los pesos actuales.

### 7.4 Limitaciones

1. **Una sola fuente.** Todo sale de Wikidata. Hereda sus sesgos de cobertura: los autores occidentales y canónicos están mejor descritos. Las 500 filas del seed son autores conocidos, así que la cobertura del 100 % no se extrapola a una lista de autores poco conocidos.
2. **La notoriedad como desempate.** La puntuación y la regla de dominancia favorecen al homónimo más famoso. Es lo correcto para este seed, pero fallaría si la lista incluyera a un autor menor con el mismo nombre que otro famoso. Sin contexto adicional (por ejemplo, un ISBN o un título de obra en el seed) no se puede distinguir.
3. **Pesos heurísticos no calibrados.** Los pesos y los umbrales no se calibraron contra un conjunto etiquetado. El análisis de sensibilidad (7.3) muestra que el resultado apenas depende de ellos en este seed, pero no garantiza lo mismo con otra lista. Cada decisión es trazable (`candidates`, `seed_resolution.note`). Mejora posible: etiquetar a mano una muestra (por ejemplo, 100 filas, incluyendo homónimos difíciles) para calibrar los pesos y medir la precisión de la resolución con una cifra real.
4. **Búsqueda solo en inglés y español.** Todos los nombres del seed están en alfabeto latino. Para nombres en otras escrituras habría que añadir idiomas de búsqueda.
5. **Comparación de nombres sin diacríticos.** Al comparar se quitan las tildes, y eso hace iguales a «Nguyễn Du» y «Nguyễn Dữ», dos escritores vietnamitas distintos. Aquí no ha causado errores (la notoriedad los separa), pero en idiomas donde los diacríticos distinguen nombres convendría comparar con ellos.
6. **Instantánea.** Los datos reflejan Wikidata en la fecha de descarga (`retrieved_at`). Una ejecución online posterior puede dar resultados distintos; la caché permite reproducir exactamente esta versión. Además, Wikidata es editable por cualquiera: el vandalismo de Vicente Huidobro (7.2) es un ejemplo real de que la fuente puede cambiar a peor entre dos descargas.
7. **Selección de valores únicos.** Para lugares con varios valores sin rango preferente se elige el de menor QID. Es determinista pero arbitrario, y queda marcado en `conflicting_fields`.
8. **Lista de no-personas escrita a mano** (`Anonymous`, `Various Authors`…). Una lista nueva podría traer otros genéricos («Anónimo», «VV. AA.», «Unknown»). Los más comunes ya están incluidos.
9. **Seudónimos.** Cada fila del seed apunta a la persona real, y `name_type` indica si usa un seudónimo, el nombre principal o el de nacimiento. Quedan dos límites: el nombre real solo se reconoce si Wikidata registra el nombre de nacimiento con una forma compatible («Mary Ann Evans» y «Theodor Seuss Geisel» quedan como `alias`), y el seudónimo no es una entidad propia, así que para atribuir obras al seudónimo (un libro firmado por «Robert Galbraith») habría que modelarlo aparte.
10. **Etiquetas en inglés.** Nombres de lugares, ocupaciones e idiomas se guardan en inglés, con respaldo en `mul` y español. `label_es` sí se guarda para el nombre del autor.
