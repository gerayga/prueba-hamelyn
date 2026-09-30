# Registro del uso de IA

**Herramienta:** Claude Code (modelo Claude Opus 5.5), en la app de escritorio, con acceso a la carpeta del proyecto, a la terminal y a GitHub (`gh`).

**Cómo se usó.** Como asistente de programación en pareja. El candidato fijó el stack (Python + SQLite + Wikidata), el alcance y los criterios de decisión. La IA propuso el plan y las reglas, escribió el código y ejecutó el pipeline. En cada paso presentaba los resultados y los casos dudosos, y el candidato elegía entre las opciones: qué hacer con los ambiguos, commitear la caché, ajustes de reglas, overrides.

| Sesión | Contenido |
|---|---|
| [01](01-analisis-y-plan.md) | Análisis del enunciado y del seed, plan, decisiones de alcance |
| [02](02-resolucion.md) | Resolución nombre → QID, primeros errores detectados (Almudena Grandes, Homer) |
| [03](03-enriquecimiento.md) | Ajustes de reglas, enriquecimiento y los problemas técnicos de fechas, etiquetas `mul`, `maxlag` y determinismo |
| [04](04-informe-calidad.md) | Informe de calidad, verificación de la muestra, corrección del desempate de fechas |
| [05](05-documentacion-y-cierre.md) | README y validación en un clon limpio |

## Decisiones tomadas por el candidato
- Stack: Python + SQLite + Wikidata. CLI sencilla. Repo en GitHub.
- Commitear la caché cruda para que el resultado sea reproducible sin red.
- Casos ambiguos: guardar el mejor candidato con baja confianza y añadir overrides manuales justificados.
- Aceptar «humano cuya existencia se discute» como persona, la regla de dominancia por sitelinks y el override de Mary Beard.
- Sacar el PDF del enunciado del repo (reescritura del historial hecha por el candidato).

## Qué se validó (y cómo)
- Cada cambio de reglas se validó con un diff de la resolución completa antes y después. Solo cambiaron los casos previstos.
- Revisión de todos los casos ambiguos, los nombres de una sola palabra, los seudónimos y los resueltos por alias, más una muestra aleatoria de 20 filas. Detalle en la §7 de `QUALITY_REPORT.md`.
- Reproducibilidad comprobada con hashes y con un test que exige resultados idénticos byte a byte, y con un clon limpio desde GitHub.

## Errores de la IA detectados durante el trabajo
Se dejan registrados porque muestran qué hizo falta revisar:
- La coincidencia de nombres usaba el texto que devolvía la API en vez de la etiqueta (Almudena Grandes salía como `partial`).
- El filtro de humanos descartaba a Homero.
- Leer fechas por SPARQL las desplazaba (años a.C. y calendario juliano). Se detectó con una prueba antes de dar el dato por bueno.
- La primera versión marcaba los IDs externos con varios valores como «conflictos», y su elección dependía de un orden no determinista.
- Un `sed` rompió `export.py` y el error se llegó a commitear. Se corrigió en el commit siguiente y se añadió un test de humo que lo habría detectado.
- El desempate de fechas por orden del API daba un año incorrecto para Ismat Chughtai. Se detectó en la muestra manual.

## Qué no se incluye
- No hay claves ni tokens: el pipeline solo usa APIs públicas sin autenticación.
- Estos ficheros son resúmenes redactados durante la sesión, no la transcripción literal.
