"""Bolsa de palabras (bag of words), n-gramas y TF-IDF hechos a mano.

Un modelo matemático no entiende texto, entiende números. La bolsa de palabras
convierte cada mensaje en un vector con una posición por palabra del vocabulario
y, en cada posición, cuántas veces aparece esa palabra. Se pierde el orden
("perro muerde hombre" = "hombre muerde perro"), pero para detectar spam funciona
sorprendentemente bien.

Mejoras del día 2:
  - n-gramas de palabras: "premio gratis" como una unidad más, que recupera algo de orden.
  - n-gramas de caracteres: "gratis" -> " gr", "gra", "rat"… Una errata ("gratiss",
    "grstis") cambia una palabra entera, pero solo unos pocos trozos de caracteres,
    así que el modelo sigue reconociendo la mayor parte.
  - TF-IDF: pondera cada término según lo raro que es en el corpus.
"""

from collections import Counter

import numpy as np

from .texto import tokenizar


def ngramas_palabras(tokens: list[str], n_min: int = 1, n_max: int = 1) -> list[str]:
    """['premio', 'gratis', 'ya'] con (1, 2) -> unigramas + 'premio gratis', 'gratis ya'."""
    resultado = []
    for n in range(n_min, n_max + 1):
        resultado.extend(" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1))
    return resultado


def ngramas_caracteres(texto: str, n_min: int = 2, n_max: int = 4) -> list[str]:
    """Trozos de n caracteres de cada palabra, con un espacio a cada lado para marcar
    el principio y el final ('gratis' -> ' gr', 'gra', …, 'is '). Los tokens especiales
    (<url>, <dinero>…) se dejan enteros: trocearlos no aporta nada."""
    resultado = []
    for palabra in tokenizar(texto, quitar_vacias=False):
        if palabra.startswith("<"):
            resultado.append(palabra)
            continue
        relleno = f" {palabra} "
        for n in range(n_min, n_max + 1):
            resultado.extend(relleno[i:i + n] for i in range(len(relleno) - n + 1))
    return resultado


class BolsaDePalabras:
    """Recuentos de términos. Un "término" puede ser una palabra, un n-grama de
    palabras (analizador="palabra", ngramas=(1, 2)) o un n-grama de caracteres
    (analizador="caracter", ngramas=(2, 4))."""

    def __init__(self, min_frecuencia: int = 1, max_palabras: int | None = None,
                 quitar_vacias: bool = True, ngramas: tuple[int, int] = (1, 1),
                 analizador: str = "palabra"):
        if analizador not in ("palabra", "caracter"):
            raise ValueError("analizador debe ser 'palabra' o 'caracter'")
        if not 1 <= ngramas[0] <= ngramas[1]:
            raise ValueError("ngramas debe ser (n_min, n_max) con 1 <= n_min <= n_max")
        self.min_frecuencia = min_frecuencia  # descarta palabras rarísimas (ruido, erratas)
        self.max_palabras = max_palabras      # limita el tamaño del vocabulario
        self.quitar_vacias = quitar_vacias
        self.ngramas = ngramas
        self.analizador = analizador
        self.vocabulario: dict[str, int] = {}  # término -> columna

    def _tokens(self, texto: str) -> list[str]:
        """Términos de un texto según el analizador elegido."""
        if self.analizador == "caracter":
            return ngramas_caracteres(texto, *self.ngramas)
        tokens = tokenizar(texto, quitar_vacias=self.quitar_vacias)
        if self.ngramas == (1, 1):
            return tokens
        return ngramas_palabras(tokens, *self.ngramas)

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
        """Lista de términos en el orden de las columnas."""
        return sorted(self.vocabulario, key=self.vocabulario.get)

    def terminos(self, texto: str) -> list[str]:
        """Términos que este vectorizador extrae de un texto (útil para explicar)."""
        return self._tokens(texto)


class TfIdf:
    """Convierte una matriz de recuentos en pesos TF-IDF.

    tf  = recuento del término en el mensaje (o 1 + log(recuento) si sublineal=True:
          que "gratis" salga 5 veces no es 5 veces más señal que 1).
    idf = log((1 + n) / (1 + df)) + 1, con n = nº de mensajes y df = en cuántos
          aparece el término. Un término que sale en todos los mensajes pesa poco;
          uno raro pesa mucho. El "+1" dentro del log es el suavizado (como si
          hubiera un documento extra con todos los términos), igual que scikit-learn.
    Después cada fila se divide por su norma L2, para que los mensajes largos y
    los cortos sean comparables.
    """

    def __init__(self, sublineal: bool = False, normalizar: bool = True):
        self.sublineal = sublineal
        self.normalizar = normalizar
        self.idf_: np.ndarray | None = None

    def ajustar(self, recuentos: np.ndarray) -> "TfIdf":
        n = recuentos.shape[0]
        df = (recuentos > 0).sum(axis=0)
        self.idf_ = np.log((1 + n) / (1 + df)) + 1.0
        return self

    def transformar(self, recuentos: np.ndarray) -> np.ndarray:
        if self.idf_ is None:
            raise RuntimeError("Llama primero a ajustar() con los recuentos de entrenamiento")
        tf = np.asarray(recuentos, dtype=np.float64).copy()
        if self.sublineal:
            positivos = tf > 0
            tf[positivos] = 1.0 + np.log(tf[positivos])
        X = tf * self.idf_
        if self.normalizar:
            normas = np.linalg.norm(X, axis=1, keepdims=True)
            normas[normas == 0] = 1.0  # mensajes sin términos conocidos: fila de ceros
            X /= normas
        return X


class VectorizadorTfIdf:
    """Bolsa de palabras + TF-IDF en un solo objeto, con la misma interfaz que
    BolsaDePalabras (ajustar / transformar / vocabulario / palabras)."""

    def __init__(self, sublineal: bool = False, **opciones_bolsa):
        self.bolsa = BolsaDePalabras(**opciones_bolsa)
        self.tfidf = TfIdf(sublineal=sublineal)

    def ajustar(self, textos: list[str]) -> "VectorizadorTfIdf":
        self.tfidf.ajustar(self.bolsa.ajustar_transformar(textos))
        return self

    def transformar(self, textos: list[str]) -> np.ndarray:
        return self.tfidf.transformar(self.bolsa.transformar(textos))

    def ajustar_transformar(self, textos: list[str]) -> np.ndarray:
        return self.ajustar(textos).transformar(textos)

    @property
    def vocabulario(self) -> dict[str, int]:
        return self.bolsa.vocabulario

    @property
    def palabras(self) -> list[str]:
        return self.bolsa.palabras

    def terminos(self, texto: str) -> list[str]:
        return self.bolsa._tokens(texto)
