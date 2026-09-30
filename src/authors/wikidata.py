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

    # --- caché -----------------------------------------------------------
    def _cache_path(self, kind: str, params: dict) -> Path:
        key = json.dumps(params, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
        return self.cache_dir / kind / f"{digest}.json"

    def _cached(self, kind: str, params: dict, fetch) -> dict:
        path = self._cache_path(kind, params)
        if path.exists():
            self.hits += 1
            return json.loads(path.read_text(encoding="utf-8"))["response"]
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
        return response

    # --- HTTP ------------------------------------------------------------
    def _request(self, method: str, url: str, **kwargs) -> dict:
        for attempt in range(5):
            time.sleep(self.delay)
            resp = self.session.request(method, url, timeout=60, **kwargs)
            if resp.status_code in (429, 500, 502, 503, 504):
                wait = int(resp.headers.get("Retry-After", 2 ** attempt * 2))
                log.warning("HTTP %s en %s, reintento en %ss", resp.status_code, url, wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and "error" in data:
                if data["error"].get("code") == "maxlag":
                    time.sleep(5)
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
            "GET", API_URL, params={**params, "maxlag": 5}))
        return data.get("search", [])

    def fulltext_humans(self, name: str, limit: int = 10) -> list[dict]:
        """Búsqueda de texto completo restringida a humanos (fallback)."""
        params = {
            "action": "query", "list": "search", "srnamespace": 0,
            "srsearch": f"{name} haswbstatement:P31=Q5", "srlimit": limit,
            "format": "json",
        }
        data = self._cached("fulltext", params, lambda: self._request(
            "GET", API_URL, params={**params, "maxlag": 5}))
        return data.get("query", {}).get("search", [])

    def sparql(self, query: str) -> list[dict]:
        params = {"query": query}
        data = self._cached("sparql", params, lambda: self._request(
            "POST", SPARQL_URL, data=params,
            headers={"Accept": "application/sparql-results+json"}))
        return data["results"]["bindings"]
