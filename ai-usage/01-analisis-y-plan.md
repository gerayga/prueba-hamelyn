# 01: Planteamiento

## Qué pedí
Que la IA leyera el enunciado y el seed, y que propusiera cambios sobre mi enfoque inicial: un repo `prueba-hamelyn`, SQLite y Wikidata. Quería el contexto completo antes de fijar un plan.

## Qué aportó la IA
- Un análisis del seed: 500 nombres, UTF-8, sin duplicados exactos. Identificó los casos trampa: siete pares seudónimo/nombre real, dos entradas que no son personas, nombres de una sola palabra, transliteraciones y autores antiguos.
- Una propuesta de plan con alternativas.

## Qué decidí
- **Stack:** Python, SQLite y Wikidata, con una CLI sencilla. Repo en GitHub.
- **Separar resolución y enriquecimiento**, guardando todos los candidatos para poder auditar cada decisión.
- **Versionar la caché cruda** para que el resultado sea reproducible sin red.
- **Casos ambiguos:** guardar el mejor candidato con confianza baja, más un fichero de overrides manuales con justificación. Descarté dejarlos sin QID.
- **Alcance:** una sola fuente. Los IDs de VIAF, ISNI y OpenLibrary se guardan para cruces futuros, pero no se consultan esas fuentes.
