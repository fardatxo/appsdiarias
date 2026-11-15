"""Lee y escribe dígitos de 8x8 "dibujados" en un fichero de texto.

Formato: hasta 8 líneas de hasta 8 caracteres. Cada carácter es un píxel:
  - espacio o punto  -> sin tinta
  - # @ X x          -> tinta al máximo
  - los caracteres de la trama " .:-=+*#%@" -> tinta de menos a más
  - un número del 0 al 9 -> tinta de 0 (nada) a 9 (máximo)
Las líneas cortas (o las que faltan) se rellenan con blanco.
"""

from pathlib import Path

import numpy as np

from .datos import LADO
from .visual import TRAMA

# intensidad (0-1) de cada carácter admitido
_INTENSIDAD = {c: i / (len(TRAMA) - 1) for i, c in enumerate(TRAMA)}
_INTENSIDAD.update({str(n): n / 9 for n in range(10)})
_INTENSIDAD.update({".": 0.0, "#": 1.0, "X": 1.0, "x": 1.0})


def texto_a_pixeles(texto):
    """Convierte el dibujo en texto a un vector de 64 valores entre 0 y 1."""
    lineas = texto.replace("\r", "").split("\n")
    while lineas and not lineas[-1].strip():  # líneas vacías del final
        lineas.pop()
    if not lineas:
        raise ValueError("El dibujo está vacío")
    if len(lineas) > LADO:
        raise ValueError(f"El dibujo tiene {len(lineas)} líneas; el máximo es {LADO}")

    imagen = np.zeros((LADO, LADO))
    for f, linea in enumerate(lineas):
        linea = linea.rstrip()
        if len(linea) > LADO:
            raise ValueError(
                f"La línea {f + 1} tiene {len(linea)} caracteres; el máximo es {LADO}"
            )
        for c, caracter in enumerate(linea):
            if caracter not in _INTENSIDAD:
                raise ValueError(f"Carácter no admitido en la línea {f + 1}: {caracter!r}")
            imagen[f, c] = _INTENSIDAD[caracter]
    if imagen.sum() == 0:
        raise ValueError("El dibujo no tiene ningún píxel con tinta")
    return imagen.ravel()


def pixeles_a_texto(pixeles):
    """Operación inversa: un carácter de la trama por píxel (8 líneas de 8)."""
    imagen = np.clip(np.asarray(pixeles, dtype=float).reshape(LADO, LADO), 0, 1)
    filas = ("".join(TRAMA[int(round(v * (len(TRAMA) - 1)))] for v in fila) for fila in imagen)
    # el blanco se escribe como "." para que no se pierda al guardar el fichero
    # (al leerlo, "." es blanco: los píxeles casi blancos pierden su pizca de tinta)
    return "\n".join(fila.replace(" ", ".") for fila in filas) + "\n"


def leer_dibujo(ruta):
    """Lee un fichero de dibujo y devuelve sus 64 píxeles."""
    ruta = Path(ruta)
    if not ruta.is_file():
        raise ValueError(f"No existe el fichero {ruta}")
    return texto_a_pixeles(ruta.read_text(encoding="utf-8"))
