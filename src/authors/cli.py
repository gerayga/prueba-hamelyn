"""CLI: python -m authors <comando>."""
import argparse
import csv
import logging
import sqlite3
from pathlib import Path

from authors import db
from authors.normalize import clean_name, match_key

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEED = ROOT / "authors_seed.csv"
DEFAULT_DB = ROOT / "data" / "authors.db"

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


COMMANDS = {
    "load": cmd_load,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="authors")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("command", choices=list(COMMANDS))
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    conn = db.connect(args.db)
    try:
        COMMANDS[args.command](conn, args)
    finally:
        conn.close()
    return 0
