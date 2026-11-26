"""Preprocesado de texto: normalizar, tokenizar y quitar palabras vacías.

Antes de que un modelo pueda "leer" un mensaje hay que convertirlo en una lista
de unidades (tokens) comparables entre sí: "GRATIS", "gratis" y "grátis" deben
contar como la misma palabra.
"""

import re
import unicodedata

# Palabras muy frecuentes que casi no aportan información para clasificar.
PALABRAS_VACIAS = frozenset(
    """
    a al algo algun alguna algunas alguno algunos ante antes como con contra cual
    cuando de del desde donde e el ella ellas ellos en entre era eres es esa esas ese
    eso esos esta estas este esto estos fue ha han has hay he la las le les lo los mas
    me mi mis muy nos o os para pero por que se ser si sin sobre son su sus te ti tu
    tus un una uno unos y ya yo
    """.split()
)

# Tokens especiales: sustituyen a cosas que varían mucho pero significan lo mismo.
TOKEN_URL = "<url>"
TOKEN_NUMERO = "<num>"
TOKEN_DINERO = "<dinero>"
TOKEN_TELEFONO = "<tel>"

_RE_URL = re.compile(r"(https?://\S+|www\.\S+|\b[a-z0-9-]+\.(?:com|es|net|org|info|xyz|ly)\S*)")
_RE_DINERO = re.compile(r"(\d+(?:[.,]\d+)?\s?(?:€|eur|euros|\$|dolares))|((?:€|\$)\s?\d+(?:[.,]\d+)?)")
_RE_TELEFONO = re.compile(r"\b(?:\+?34\s?)?[6789]\d{2}\s?\d{3}\s?\d{3}\b")
_RE_NUMERO = re.compile(r"\b\d+(?:[.,]\d+)?\b")
_RE_PALABRA = re.compile(r"<[a-z]+>|[a-zñ]+|[!¡]")


def quitar_tildes(texto: str) -> str:
    """'canción' -> 'cancion'. Conserva la ñ, que en español cambia el significado."""
    texto = texto.replace("ñ", "\0").replace("Ñ", "\1")
    sin = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    return sin.replace("\0", "ñ").replace("\1", "Ñ")


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y con URLs, teléfonos, cantidades y números sustituidos."""
    texto = quitar_tildes(texto.lower())
    texto = _RE_URL.sub(f" {TOKEN_URL} ", texto)
    texto = _RE_DINERO.sub(f" {TOKEN_DINERO} ", texto)
    texto = _RE_TELEFONO.sub(f" {TOKEN_TELEFONO} ", texto)
    texto = _RE_NUMERO.sub(f" {TOKEN_NUMERO} ", texto)
    return texto


def tokenizar(texto: str, quitar_vacias: bool = True) -> list[str]:
    """Convierte un mensaje en una lista de tokens.

    Las exclamaciones se guardan como token "!" (el spam abusa de ellas).
    """
    tokens = _RE_PALABRA.findall(normalizar(texto))
    tokens = ["!" if t == "¡" else t for t in tokens]
    if quitar_vacias:
        tokens = [t for t in tokens if t not in PALABRAS_VACIAS]
    # Palabras de una sola letra casi nunca aportan (salvo la exclamación).
    return [t for t in tokens if len(t) > 1 or t == "!"]
