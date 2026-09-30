"""Normalización de nombres.

El nombre original del seed se conserva siempre; estas funciones solo sirven
para comparar y puntuar candidatos.
"""
import re
import unicodedata

_WS = re.compile(r"\s+")


def clean_name(raw: str) -> str:
    """NFC + espacios colapsados. Es la forma canónica que se guarda."""
    return _WS.sub(" ", unicodedata.normalize("NFC", raw)).strip()


def match_key(name: str) -> str:
    """Clave de comparación: sin tildes, minúsculas, sin puntuación.

    'J. K. Rowling' -> 'j k rowling'; 'Kenzaburō Ōe' -> 'kenzaburo oe'.
    """
    decomposed = unicodedata.normalize("NFKD", name)
    no_marks = "".join(c for c in decomposed if not unicodedata.combining(c))
    no_punct = re.sub(r"[^\w\s]", " ", no_marks.casefold())
    return _WS.sub(" ", no_punct).strip()


# Precisiones de fecha de Wikidata (wikibase:timePrecision).
PRECISION_NAMES = {
    0: "billion_years", 3: "million_years", 4: "100k_years", 5: "10k_years",
    6: "millennium", 7: "century", 8: "decade", 9: "year", 10: "month", 11: "day",
}
CALENDARS = {
    "http://www.wikidata.org/entity/Q1985727": "gregorian",
    "http://www.wikidata.org/entity/Q1985786": "julian",
}


def parse_wikidata_time(time: str, precision: int) -> tuple[str, int]:
    """Convierte un valor de tiempo del JSON de Wikidata a (fecha ISO truncada, año).

    Se usa el valor original (no el de SPARQL, que desplaza los años a.C. una
    unidad y convierte las fechas julianas a gregoriano). Año negativo = a.C.
    '+1547-09-29T00:00:00Z', 11 -> ('1547-09-29', 1547)
    '-0630-00-00T00:00:00Z', 9  -> ('-0630', -630)
    """
    sign = -1 if time.startswith("-") else 1
    year_str, month, day = time.lstrip("+-").split("T")[0].split("-")
    year = sign * int(year_str)
    out = f"{'-' if year < 0 else ''}{abs(year):04d}"
    if precision >= 10 and month != "00":
        out += f"-{month}"
        if precision >= 11 and day != "00":
            out += f"-{day}"
    return out, year
