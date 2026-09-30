"""Export CSV de las vistas planas."""
import csv
import logging
import sqlite3
from pathlib import Path

log = logging.getLogger(__name__)

EXPORTS = {
    "authors.csv": "SELECT * FROM v_authors_flat ORDER BY label",
    "seed_resolution.csv": "SELECT * FROM v_seed_resolution ORDER BY seed_id",
}


def run(conn: sqlite3.Connection, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, query in EXPORTS.items():
        cur = conn.execute(query)
        with open(out_dir / name, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([d[0] for d in cur.description])
            rows = cur.fetchall()
            writer.writerows(rows)
        log.info("Exportado %s (%d filas)", name, len(rows))
