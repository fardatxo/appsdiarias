"""Bolsa de palabras (bag of words) hecha a mano.

Un modelo matemático no entiende texto, entiende números. La bolsa de palabras
convierte cada mensaje en un vector con una posición por palabra del vocabulario
y, en cada posición, cuántas veces aparece esa palabra. Se pierde el orden
("perro muerde hombre" = "hombre muerde perro"), pero para detectar spam funciona
sorprendentemente bien.
"""

from collections import Counter

import numpy as np

from .texto import tokenizar


class BolsaDePalabras:
    def __init__(self, min_frecuencia: int = 1, max_palabras: int | None = None,
                 quitar_vacias: bool = True):
        self.min_frecuencia = min_frecuencia  # descarta palabras rarísimas (ruido, erratas)
        self.max_palabras = max_palabras      # limita el tamaño del vocabulario
        self.quitar_vacias = quitar_vacias
        self.vocabulario: dict[str, int] = {}  # palabra -> columna

    def _tokens(self, texto: str) -> list[str]:
        return tokenizar(texto, quitar_vacias=self.quitar_vacias)

    def ajustar(self, textos: list[str]) -> "BolsaDePalabras":
        """Aprende el vocabulario SOLO con los textos de entrenamiento."""
        cuentas = Counter()
        for texto in textos:
            cuentas.update(self._tokens(texto))
        candidatas = [(p, c) for p, c in cuentas.items() if c >= self.min_frecuencia]
        # Orden: más frecuentes primero; a igualdad, alfabético (determinista).
        candidatas.sort(key=lambda pc: (-pc[1], pc[0]))
        if self.max_palabras is not None:
            candidatas = candidatas[: self.max_palabras]
        palabras = sorted(p for p, _ in candidatas)
        self.vocabulario = {p: i for i, p in enumerate(palabras)}
        return self

    def transformar(self, textos: list[str]) -> np.ndarray:
        """Matriz (n_textos, n_palabras) de recuentos. Ignora palabras desconocidas."""
        if not self.vocabulario:
            raise RuntimeError("Llama primero a ajustar() con los textos de entrenamiento")
        X = np.zeros((len(textos), len(self.vocabulario)), dtype=np.float64)
        for fila, texto in enumerate(textos):
            for token in self._tokens(texto):
                col = self.vocabulario.get(token)
                if col is not None:
                    X[fila, col] += 1
        return X

    def ajustar_transformar(self, textos: list[str]) -> np.ndarray:
        return self.ajustar(textos).transformar(textos)

    @property
    def palabras(self) -> list[str]:
        """Lista de palabras en el orden de las columnas."""
        return sorted(self.vocabulario, key=self.vocabulario.get)
