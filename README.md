# prueba-hamelyn — Base de datos de autores

Enriquece `authors_seed.csv` con información pública de Wikidata y la guarda en SQLite.

> En construcción. Las instrucciones completas y las decisiones técnicas se añadirán al final.

## Ejecución rápida

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"   # en Linux/macOS: .venv/bin/python
.venv/Scripts/python -m authors load
```
