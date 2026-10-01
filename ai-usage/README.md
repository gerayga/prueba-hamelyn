# Uso de IA

He usado **Claude Code** (Claude Opus 5.5) como asistente durante toda la prueba.

## Reparto de trabajo

| Yo | La IA |
|---|---|
| Acotar el problema: fuente (Wikidata), almacenamiento (SQLite), forma de entrega (repo, CLI) | Analizar el seed y proponer un plan y alternativas |
| Decidir en cada punto abierto qué opción aplicar | Escribir el código, los tests y la documentación |
| Revisar los resultados y los casos dudosos antes de aprobar cada paso | Ejecutar el pipeline y las comprobaciones sobre los datos |
| Resolver a mano los casos que las reglas no deciden (overrides) | Presentar cifras, diffs y casos límite para la revisión |

El código lo escribió la IA. Mi trabajo fue el planteamiento, las decisiones de diseño y calidad, y la revisión de los resultados en cada paso.

## Decisiones que tomé

El enfoque inicial (Wikidata, SQLite, un repo) fue mío. En el resto de puntos, la IA planteó alternativas y yo elegí; algunas soluciones técnicas las propuso la IA al detectar un problema y yo las aprobé (marcadas con *).

| Decisión | Opciones valoradas | Por qué |
|---|---|---|
| Wikidata como única fuente | Añadir OpenLibrary o VIAF | Tiene identificadores estables y ya enlaza con VIAF, ISNI y OpenLibrary. Varias fuentes multiplican la reconciliación; en 2-3 h prefiero una sola bien resuelta. |
| SQLite y CLI sencilla | Postgres, notebooks | Un único fichero, sin servidor, fácil de revisar y de reproducir. |
| Separar resolución (nombre → QID) y enriquecimiento | Hacerlo todo en un paso | El riesgo está en identificar bien a cada persona. Quiero esa decisión auditable y corregible sin tocar el resto. |
| Versionar la caché cruda de Wikidata | No versionarla y descargar en cada ejecución | Reproducibilidad exacta y ejecución sin red. Wikidata cambia continuamente. |
| Casos ambiguos: guardar el mejor candidato con confianza baja + overrides manuales | Dejarlos sin QID | No se pierde información, queda trazado y la decisión humana está documentada. |
| Aceptar «humano cuya existencia se discute» (Q21070568) como persona | Resolver Homero con un override | Es una regla general que vale para otras figuras semilegendarias, no un parche puntual. |
| Regla de dominancia (≥ 5× sitelinks) | Resolver los 13 ambiguos con overrides | Los 13 eran homónimos muy menores. Una regla generaliza mejor que 13 excepciones manuales. |
| Override de Mary Beard → la clasicista | Dejarla como ambigua | Dos candidatas con notoriedad parecida. El contexto del seed (divulgación actual) decide. |
| Seudónimos: la fila del seed apunta a la persona real | Tratar el seudónimo como entidad propia | Para una base de autores interesa la persona. El seudónimo se conserva como nombre. |
| Fechas con su precisión y calendario originales* | Normalizar a `DATE` | Un «siglo VII a.C.» no es una fecha exacta. Normalizar inventaría precisión. |
| Validar los pesos de la puntuación con un análisis de sensibilidad (y mantener los actuales) | Cambiarlos sin más datos · sustituir la puntuación por reglas en orden | Los pesos no se pueden calibrar sin un conjunto etiquetado, así que investigué cómo cambiaba el resultado al variarlos (ver abajo). |
| Informe de calidad generado desde los datos + notas manuales aparte* | Informe escrito a mano | Las cifras no se desactualizan y el análisis manual no se pisa al regenerar. |
| No distribuir el enunciado en el repo | — | Lo retiré del historial. |

### Sobre los pesos de la puntuación

> Los pesos son una heurística, pero comprobé que apenas condicionan el resultado: en 171 combinaciones, 493 de 498 resoluciones no cambian nunca. De las 5 restantes, 4 solo cambian si una señal se lleva al extremo; la excepción es Jane Goodall, un caso límite real (primatóloga con libros frente a una escritora homónima) que queda señalado en el informe. Lo que importa es combinar las tres señales, no el valor exacto de cada peso.

Reproducible con `python scripts/sensitivity.py`; detalle en la §7.3 de `QUALITY_REPORT.md`.

## Qué se revisó antes de aprobar cada paso

La IA ejecutó las comprobaciones y me presentó los resultados; yo los revisé antes de aprobar el paso siguiente.

- Los 14 casos ambiguos de la primera ejecución, antes de decidir las reglas.
- El diff de la resolución completa antes y después de cada cambio de reglas: solo debían cambiar los casos previstos.
- Los seudónimos, los nombres de una sola palabra y los resueltos por alias.
- Una muestra aleatoria de 20 filas. Detalle en la §7 de `QUALITY_REPORT.md`.
- Que el pipeline se reproduce idéntico desde un clon limpio de GitHub.

## Problemas detectados durante la validación

Los incluyo porque muestran que ningún resultado se dio por bueno sin comprobarlo:

- **Homero resolvía a Winslow Homer.** En Wikidata no está clasificado como «humano». Se resolvió con una regla.
- **Fechas mal en SPARQL.** El endpoint SPARQL desplaza un año las fechas a.C. y convierte las julianas a gregoriano. Se cambió la fuente de las fechas al JSON original.
- **Ismat Chughtai con el año de nacimiento incorrecto**, detectado en la muestra manual. Se cambió el criterio de desempate a «más referencias».
- **Autores sin etiqueta.** Wikidata introdujo en 2024 las etiquetas `mul` (válidas para todos los idiomas). Se añadieron como respaldo.
- **Resultados no deterministas** (orden de SPARQL, fecha de ejecución). Se corrigió y ahora hay un test que exige resultados idénticos byte a byte.

## Detalle por sesión

[01 Planteamiento](01-analisis-y-plan.md) · [02 Resolución](02-resolucion.md) · [03 Enriquecimiento](03-enriquecimiento.md) · [04 Calidad](04-informe-calidad.md) · [05 Cierre](05-documentacion-y-cierre.md)

No se incluyen claves ni tokens: el pipeline solo usa APIs públicas sin autenticación.
