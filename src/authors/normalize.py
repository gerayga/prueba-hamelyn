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
