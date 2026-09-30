# Sesión 05: documentación y cierre

## Prompt del candidato
- "Sí" (continuar con el paso 6: README y repaso de `ai-usage/`).

## Qué hizo la IA
- Escribió el README completo: ejecución, comandos, diagrama del flujo, estructura, modelo de datos, decisiones técnicas y cómo añadir overrides. Todas las cifras salen de consultas a la BD, no de memoria.
- Al redactarlo detectó que la búsqueda de respaldo de texto completo no se activó nunca con este seed (0 entradas `fulltext` en la caché). El README lo dice así en lugar de presentarla como si hubiera aportado algo.
- Corrigió el contador de peticiones del log: `enrich` mostraba las acumuladas de todo el pipeline.

## Validación
- **Clon limpio desde GitHub** en un directorio temporal, siguiendo el README tal cual: `pip install -e ".[dev]"`, `run --offline` y `pytest` (21 tests OK). Tras la ejecución `git status` no muestra ningún cambio: la BD, los CSV y el informe son idénticos byte a byte a los commiteados.
