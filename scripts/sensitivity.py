"""Análisis de sensibilidad de los parámetros de resolución.

Recalcula la resolución de las 498 filas (offline, desde data/cache) con
distintos pesos, umbral, margen y factor de dominancia, y cuenta cuántas
decisiones cambian respecto a la configuración actual.

    python scripts/sensitivity.py
"""
import copy
import itertools
import sqlite3
from collections import defaultdict
from pathlib import Path

from authors import resolve
from authors.wikidata import WikidataClient

ROOT = Path(__file__).resolve().parents[1]
BASE_WEIGHTS = (resolve.W_NAME, resolve.W_LITERARY, resolve.W_POPULARITY)
BASE_PARAMS = (resolve.MATCH_THRESHOLD, resolve.MIN_MARGIN, resolve.DOMINANCE_RATIO)


def load_candidates() -> tuple[dict[int, list], dict[int, str]]:
    client = WikidataClient(ROOT / "data" / "cache", offline=True)
    conn = sqlite3.connect(ROOT / "data" / "authors.db")
    conn.row_factory = sqlite3.Row
    seeds = [s for s in conn.execute("SELECT seed_id, clean_name, match_key FROM seed_names")
             if s["match_key"] not in resolve.NON_PERSON_KEYS]
    per_seed = {s["seed_id"]: resolve.search_candidates(client, s["clean_name"]) for s in seeds}
    facts = resolve.fetch_facts(client, [c.qid for cs in per_seed.values() for c in cs])
    for cs in per_seed.values():
        for c in cs:
            f = facts.get(c.qid, {})
            c.is_human, c.is_writer = f.get("human", False), f.get("writer", False)
            c.has_works, c.sitelinks = f.get("works", False), f.get("sitelinks", 0)
    return per_seed, {s["seed_id"]: s["clean_name"] for s in seeds}


def evaluate(per_seed, weights, threshold, margin, dominance) -> dict[int, tuple]:
    resolve.W_NAME, resolve.W_LITERARY, resolve.W_POPULARITY = weights
    resolve.MATCH_THRESHOLD, resolve.MIN_MARGIN, resolve.DOMINANCE_RATIO = threshold, margin, dominance
    out = {}
    for sid, cands in per_seed.items():
        cands = copy.deepcopy(cands)
        for c in cands:
            c.score = resolve.score_candidate(c)
        status, best, _, _ = resolve.decide(cands)
        out[sid] = (status, best.qid if best else None)
    return out


def main() -> None:
    per_seed, names = load_candidates()
    base = evaluate(per_seed, BASE_WEIGHTS, *BASE_PARAMS)

    def compare(weights=BASE_WEIGHTS, threshold=BASE_PARAMS[0], margin=BASE_PARAMS[1],
                dominance=BASE_PARAMS[2]):
        res = evaluate(per_seed, weights, threshold, margin, dominance)
        qid = sorted(s for s in res if res[s][1] != base[s][1])
        status = sorted(names[s] for s in res if res[s][1] == base[s][1] and res[s][0] != base[s][0])
        return qid, status

    print(f"Configuración actual: pesos {BASE_WEIGHTS}, umbral {BASE_PARAMS[0]}, "
          f"margen {BASE_PARAMS[1]}, dominancia {BASE_PARAMS[2]}x. Filas evaluadas: {len(base)}\n")

    print("## Pesos (nombre, literario, notoriedad)\n")
    print("| Pesos | QID distinto | Cambio de estado |\n|---|---|---|")
    for w in [(0.50, 0.30, 0.20), (0.34, 0.33, 0.33), (0.60, 0.20, 0.20), (0.30, 0.30, 0.40),
              (0.20, 0.40, 0.40), (0.50, 0.50, 0.00), (0.70, 0.30, 0.00)]:
        qid, status = compare(weights=w)
        qid_names = sorted(names[s] for s in qid)
        print(f"| {w} | {len(qid)} {qid_names or ''} | {len(status)} {status or ''} |")

    grid = [(a / 100, b / 100, round(1 - (a + b) / 100, 2))
            for a, b in itertools.product(range(5, 95, 5), repeat=2) if a + b <= 95]
    changed_by = defaultdict(list)
    stable = set(base)
    for w in grid:
        for sid in compare(weights=w)[0]:
            changed_by[names[sid]].append(w)
            stable.discard(sid)
    unchanged = sum(1 for w in grid if not compare(weights=w)[0])
    print(f"\n## Barrido de pesos: {len(grid)} combinaciones (pasos de 0.05, cada peso >= 0.05)\n")
    print(f"- Combinaciones con exactamente los mismos QIDs: {unchanged}/{len(grid)}")
    print(f"- Filas con el mismo QID en todas las combinaciones: {len(stable)}/{len(base)}")
    for name, ws in sorted(changed_by.items(), key=lambda kv: -len(kv[1])):
        rng = [f"{lbl} {min(w[i] for w in ws)}–{max(w[i] for w in ws)}"
               for i, lbl in enumerate(("nombre", "literario", "notoriedad"))]
        print(f"- {name}: cambia en {len(ws)} combinaciones ({', '.join(rng)})")

    print("\n## Umbral, margen y dominancia (pesos actuales)\n")
    print("| Parámetro | Valor | QID distinto | Cambio de estado |\n|---|---|---|---|")
    for t in (0.5, 0.6, 0.7, 0.8):
        qid, status = compare(threshold=t)
        print(f"| umbral | {t} | {len(qid)} | {len(status)} {status or ''} |")
    for m in (0.05, 0.10, 0.15, 0.20, 0.30):
        qid, status = compare(margin=m)
        print(f"| margen | {m} | {len(qid)} | {len(status)} {status or ''} |")
    for d in (2, 3, 5, 10, 20, float("inf")):
        qid, status = compare(dominance=d)
        print(f"| dominancia | {'sin' if d == float('inf') else f'{d}x'} | {len(qid)} | {len(status)} |")


if __name__ == "__main__":
    main()
