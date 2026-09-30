# Sesión 03: ajustes de resolución, enriquecimiento y export

## Prompts del candidato
- "Sí, aplica 1, 2 y 3 y sigue con el paso 4. Ya hice lo del PDF también."

## Decisiones del candidato
- Se acepta Q21070568 ("humano cuya existencia se discute") como persona. Arregla Homer.
- Se aplica la regla de dominancia: el margen no se exige si el mejor candidato tiene al menos 5 veces los sitelinks del segundo.
- Override manual de Mary Beard → Q458403 (clasicista), con la alternativa descartada documentada.

## Validación hecha por la IA
- Diff de la resolución antes y después de los ajustes: solo cambian los 14 casos ambiguos, y el único QID distinto es el de Homer.
- El `echo` de PowerShell que usó el candidato escribió `*.pdf` en UTF-16 dentro de `.gitignore`. Git lo interpretaba como `*` y ignoraba todos los archivos nuevos. Detectado con `git check-ignore` y corregido.

## Hallazgos técnicos durante el enriquecimiento
1. **Las fechas de SPARQL no son fiables para a.C. ni para el calendario juliano.** WDQS usa XSD 1.1: "630 a.C." (-0630 en el JSON) llega como -0629, y las fechas julianas se convierten a gregoriano (Cervantes: 29-09-1547 juliano → 1547-10-09). Por eso las fechas se leen con `wbgetclaims`, que da el JSON original, y se guardan con su precisión y su calendario.
2. **Varios valores por propiedad.** Safo tiene 9 fechas de nacimiento. Se aplica la semántica de "best rank": se ignoran las deprecated y, si hay preferred, solo cuentan las preferred. Los conflictos que quedan se marcan en `conflicting_fields`.
3. **Los IDs externos son multivalor legítimo** (varios VIAF o ISNI). En la primera versión se marcaban como conflicto y se elegía "el primero" según el orden de SPARQL, que no es determinista. Ahora se guardan todos, ordenados.
4. **Etiquetas `mul`.** Desde 2024 Wikidata tiene etiquetas válidas para todos los idiomas, y 4 autores (Rowling, Hugo, Kipling, Almudena Grandes) no tenían etiqueta `en`. Se añadió `mul` como respaldo.
5. **Rate limiting.** El parámetro `maxlag=5` hacía fallar las lecturas cuando la replicación de Wikidata iba con retraso. Se quitó, porque solo tiene sentido para bots que editan, y se reforzó el backoff ante 429.
6. **Reproducibilidad.** `retrieved_at` usaba la hora de ejecución y rompía el determinismo. Ahora es la fecha de descarga guardada en la caché. Verificado: dos `run --offline` dan CSV idénticos (sha1).
7. `--prune-cache` elimina de la caché las respuestas de consultas antiguas que ya no se usan (71 entradas).
