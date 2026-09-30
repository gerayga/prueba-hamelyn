# prueba-hamelyn — Base de datos de autores

Enriquece `authors_seed.csv` con información pública de Wikidata y la guarda en SQLite.

> En construcción. Las instrucciones completas y las decisiones técnicas se añadirán al final.

## Ejecución rápida

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"   # en Linux/macOS: .venv/bin/python
.venv/Scripts/python -m authors run --offline   # reconstruye la BD solo desde data/cache
```

Comandos: `load`, `resolve`, `enrich`, `export`, `report` y `run` (todos los anteriores, con la BD desde cero).
Opciones: `--offline` (no usa la red), `--prune-cache` (con `run`), `--limit N`.
