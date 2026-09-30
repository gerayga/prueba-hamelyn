"""Cliente mínimo de Wikidata con caché en disco.

Cada petición se guarda en data/cache/<kind>/<sha1>.json junto con sus
parámetros. Con offline=True solo se lee de la caché, lo que hace que el
pipeline sea reproducible sin red y con exactamente los mismos datos.
"""
import hashlib
import json
import logging
import time
from pathlib import Path

import requests

API_URL = "https://www.wikidata.org/w/api.php"
SPARQL_URL = "https://query.wikidata.org/sparql"
USER_AGENT = "prueba-hamelyn/0.1 (https://github.com/gerayga/prueba-hamelyn; python-requests)"

log = logging.getLogger(__name__)


class CacheMiss(RuntimeError):
    pass


class WikidataClient:
    def __init__(self, cache_dir: Path, offline: bool = False, delay: float = 0.1):
        self.cache_dir = cache_dir
        self.offline = offline
        self.delay = delay
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.hits = 0
        self.misses = 0
        self.used: set[Path] = set()
        self.last_retrieved_at: str | None = None  # fecha de descarga de la última respuesta

    # --- caché -----------------------------------------------------------
    def _cache_path(self, kind: str, params: dict) -> Path:
        key = json.dumps(params, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
        return self.cache_dir / kind / f"{digest}.json"

    def _cached(self, kind: str, params: dict, fetch) -> dict:
        path = self._cache_path(kind, params)
        self.used.add(path)
        if path.exists():
            self.hits += 1
            cached = json.loads(path.read_text(encoding="utf-8"))
            self.last_retrieved_at = cached["retrieved_at"]
            return cached["response"]
        if self.offline:
            raise CacheMiss(f"Sin caché para {kind} {params}")
        self.misses += 1
        response = fetch()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "params": params,
            "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "response": response,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        self.last_retrieved_at = payload["retrieved_at"]
        return response

    def prune_unused(self) -> int:
        """Borra de la caché las respuestas que esta ejecución no ha usado."""
        removed = 0
        for path in self.cache_dir.rglob("*.json"):
            if path not in self.used:
                path.unlink()
                removed += 1
        return removed

    # --- HTTP ------------------------------------------------------------
    def _request(self, method: str, url: str, **kwargs) -> dict:
        for attempt in range(8):
            time.sleep(self.delay)
            resp = self.session.request(method, url, timeout=60, **kwargs)
            if resp.status_code in (429, 500, 502, 503, 504):
                # Backoff exponencial; Retry-After solo como mínimo. Tras un 429 se
                # ralentiza el ritmo de todas las peticiones siguientes.
                retry_after = int(resp.headers.get("Retry-After", 0) or 0)
                wait = max(retry_after, 2 ** attempt * 2)
                if resp.status_code == 429:
                    self.delay = min(self.delay * 2, 2.0)
                log.warning("HTTP %s en %s, reintento en %ss (delay=%.2fs)",
                            resp.status_code, url, wait, self.delay)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and "error" in data:
                if data["error"].get("code") == "maxlag":
                    # No usamos maxlag (solo leemos), pero se trata por si acaso.
                    log.warning("maxlag en %s, reintento en 10s", url)
                    time.sleep(10)
                    continue
                raise RuntimeError(f"Error de la API: {data['error']}")
            return data
        raise RuntimeError(f"Agotados los reintentos para {url}")

    # --- endpoints -------------------------------------------------------
    def search_entities(self, name: str, lang: str, limit: int = 10) -> list[dict]:
        """Búsqueda por prefijo de etiqueta/alias (wbsearchentities)."""
        params = {
            "action": "wbsearchentities", "search": name, "language": lang,
            "uselang": lang, "type": "item", "limit": limit, "format": "json",
        }
        data = self._cached("search", params, lambda: self._request(
            "GET", API_URL, params=params))
        return data.get("search", [])

    def fulltext_humans(self, name: str, limit: int = 10) -> list[dict]:
        """Búsqueda de texto completo restringida a humanos (fallback)."""
        params = {
            "action": "query", "list": "search", "srnamespace": 0,
            "srsearch": f"{name} haswbstatement:P31=Q5", "srlimit": limit,
            "format": "json",
        }
        data = self._cached("fulltext", params, lambda: self._request(
            "GET", API_URL, params=params))
        return data.get("query", {}).get("search", [])

    def get_claims(self, qid: str, prop: str) -> list[dict]:
        """Statements originales (JSON) de una propiedad de una entidad."""
        params = {"action": "wbgetclaims", "entity": qid, "property": prop, "format": "json"}
        data = self._cached("claims", params, lambda: self._request(
            "GET", API_URL, params=params))
        return data.get("claims", {}).get(prop, [])

    def sparql(self, query: str) -> list[dict]:
        params = {"query": query}
        data = self._cached("sparql", params, lambda: self._request(
            "POST", SPARQL_URL, data=params,
            headers={"Accept": "application/sparql-results+json"}))
        return data["results"]["bindings"]
