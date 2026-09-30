# Sesión 01 — Análisis del enunciado y plan

**Herramienta:** Claude Code (Claude Opus 5.5), app de escritorio.
**Fecha:** 2026-09-30

## Prompts del candidato (resumidos)
1. "Échale un ojo a los archivos de la carpeta, es una prueba técnica. Hay que hacer un repo (prueba-hamelyn), usar SQLite y Wikidata. Dime si cambiarías algo."
2. "Python sí, repo en GitHub (cuenta gerayga), CLI simple, y guarda ai-usage."

## Qué hizo la IA
- Leyó el PDF del enunciado y `authors_seed.csv` (500 filas, UTF-8, sin duplicados exactos).
- Identificó casos trampa en el seed:
  - Seudónimos y nombres reales de la misma persona (Robert Galbraith / J. K. Rowling, Samuel Clemens / Mark Twain, Mary Ann Evans / George Eliot, Émile Ajar / Romain Gary, Isak Dinesen / Karen Blixen, Charles Lutwidge Dodgson / Lewis Carroll, Theodor Seuss Geisel / Dr. Seuss).
  - Entradas que no son personas (`Anonymous`, `Various Authors`).
  - Nombres de una sola palabra, ambiguos (Homer, Adonis, Colette, Azorín…).
  - Transliteraciones y diacríticos, autores de no ficción y autores de la Antigüedad.
- Propuso separar la resolución (nombre → QID) del enriquecimiento (QID → atributos), cachear las respuestas crudas, guardar la confianza y el método de cada coincidencia, y generar el informe de calidad a partir de los datos.

## Decisiones tomadas por el candidato
- Stack: Python + SQLite + Wikidata.
- Repositorio en GitHub: `gerayga/prueba-hamelyn`.
- CLI simple.
- Registrar el uso de IA en esta carpeta.

## Pendiente de validar por el candidato
- Las reglas de matching y los umbrales de confianza (ver el plan).

## Decisiones confirmadas tras el plan
- Commitear `data/cache/` para reproducibilidad offline: **sí**.
- Casos ambiguos: **(b)** guardar el mejor candidato con baja confianza + **(c)** `data/overrides.csv` con resoluciones manuales del candidato.

## Paso 1 completado
- Esqueleto del paquete (`src/authors`), esquema SQLite, normalización de nombres, comando `load` idempotente y tests de normalización.
- Repo creado en GitHub como privado: `gerayga/prueba-hamelyn`.
- Validado: 500 filas cargadas, `load` ejecutado dos veces sin duplicar, 2 tests OK.
