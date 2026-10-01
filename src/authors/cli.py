"""CLI: python -m authors <comando>."""
import argparse
import csv
import logging
import sqlite3
from pathlib import Path

from authors import db, enrich, export, report, resolve
from authors.wikidata import WikidataClient
from authors.normalize import clean_name, match_key

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEED = ROOT / "authors_seed.csv"
DEFAULT_DB = ROOT / "data" / "authors.db"
CACHE_DIR = ROOT / "data" / "cache"
OVERRIDES = ROOT / "data" / "overrides.csv"
CORRECTIONS = ROOT / "data" / "corrections.csv"
EXPORT_DIR = ROOT / "data" / "export"
REPORT = ROOT / "QUALITY_REPORT.md"
QUALITY_NOTES = ROOT / "docs" / "quality_notes.md"

log = logging.getLogger("authors")


def cmd_load(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    with open(args.seed, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != ["author_name"]:
            raise SystemExit(f"Cabecera inesperada en el seed: {reader.fieldnames}")
        rows = [
            (i, r["author_name"], clean_name(r["author_name"]), match_key(r["author_name"]))
            for i, r in enumerate(reader, start=1)
            if r["author_name"].strip()
        ]
    with conn:
        conn.executemany(
            """INSERT INTO seed_names (seed_id, raw_name, clean_name, match_key)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(seed_id) DO UPDATE SET
                 raw_name=excluded.raw_name,
                 clean_name=excluded.clean_name,
                 match_key=excluded.match_key""",
            rows,
        )
    log.info("Cargadas %d filas del seed", len(rows))


def get_client(args: argparse.Namespace) -> WikidataClient:
    # Un único cliente por ejecución, para poder saber qué entradas de caché se usaron.
    if getattr(args, "client", None) is None:
        args.client = WikidataClient(CACHE_DIR, offline=args.offline)
    return args.client


def cmd_resolve(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    client = get_client(args)
    resolve.run(conn, client, OVERRIDES, limit=args.limit)
    for row in conn.execute(
        "SELECT status, COUNT(*) n FROM seed_resolution GROUP BY status ORDER BY n DESC"
    ):
        log.info("  %-13s %d", row["status"], row["n"])


def cmd_enrich(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    enrich.run(conn, get_client(args), CORRECTIONS)


def cmd_export(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    export.run(conn, args.export_dir)


def cmd_report(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    report.run(conn, args.report, QUALITY_NOTES)


def cmd_run(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    """Pipeline completo. La BD se reconstruye desde cero (la caché se conserva)."""
    for step in (cmd_load, cmd_resolve, cmd_enrich, cmd_export, cmd_report):
        log.info("== %s ==", step.__name__.removeprefix("cmd_"))
        step(conn, args)
    if args.prune_cache:
        log.info("Caché: %d entradas sin usar eliminadas", get_client(args).prune_unused())


COMMANDS = {
    "load": cmd_load,
    "resolve": cmd_resolve,
    "enrich": cmd_enrich,
    "export": cmd_export,
    "report": cmd_report,
    "run": cmd_run,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="authors")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--export-dir", type=Path, default=EXPORT_DIR)
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--offline", action="store_true",
                        help="usar solo la caché de data/cache (sin red)")
    parser.add_argument("--prune-cache", action="store_true",
                        help="(run) borrar de la caché las respuestas no usadas")
    parser.add_argument("--limit", type=int, help="procesar solo las N primeras filas")
    parser.add_argument("command", choices=list(COMMANDS))
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    if args.command == "run" and args.db.exists():
        args.db.unlink()
    conn = db.connect(args.db)
    try:
        COMMANDS[args.command](conn, args)
    finally:
        conn.close()
    return 0
