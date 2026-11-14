"""Clasificador k-NN (k vecinos más cercanos) implementado con numpy.

Idea: para clasificar una imagen nueva, se buscan las k imágenes de entrenamiento
que más se le parecen (menor distancia) y se elige el dígito más votado entre ellas.
No hay "entrenamiento" real: el modelo simplemente memoriza los ejemplos.
"""

import numpy as np


def distancias_euclideas(A, B):
    """Matriz de distancias entre cada fila de A y cada fila de B.

    Usa la identidad |a-b|² = |a|² + |b|² - 2·a·b para calcularlo todo de golpe
    con operaciones de matrices, sin bucles de Python (mucho más rápido).
    """
    A = np.asarray(A, dtype=float)
    B = np.asarray(B, dtype=float)
    cuadrados = (
        np.sum(A**2, axis=1)[:, None] + np.sum(B**2, axis=1)[None, :] - 2 * A @ B.T
    )
    # Los errores de redondeo pueden dar valores negativos diminutos
    return np.sqrt(np.maximum(cuadrados, 0))


class ClasificadorKNN:
    """k-NN con voto por mayoría."""

    def __init__(self, k=3):
        if not isinstance(k, (int, np.integer)) or k < 1:
            raise ValueError("k debe ser un entero mayor o igual que 1")
        self.k = int(k)
        self.X_train = None
        self.y_train = None
        self.clases = None

    def entrenar(self, X, y):
        """Memoriza los ejemplos de entrenamiento."""
        X = np.asarray(X, dtype=float)
        y = np.asarray(y)
        if X.ndim != 2:
            raise ValueError("X debe ser una matriz (ejemplos x características)")
        if len(X) != len(y):
            raise ValueError("X e y deben tener el mismo número de ejemplos")
        if self.k > len(X):
            raise ValueError(f"k={self.k} es mayor que el número de ejemplos ({len(X)})")
        self.X_train = X
        self.y_train = y
        self.clases = np.unique(y)
        return self

    def _comprobar_entrenado(self):
        if self.X_train is None:
            raise RuntimeError("El modelo no está entrenado: llama antes a entrenar()")

    def vecinos(self, X):
        """Índices y distancias de los k vecinos más cercanos de cada fila de X."""
        self._comprobar_entrenado()
        X = np.atleast_2d(np.asarray(X, dtype=float))
        if X.shape[1] != self.X_train.shape[1]:
            raise ValueError(
                f"Se esperaban {self.X_train.shape[1]} características, "
                f"pero llegaron {X.shape[1]}"
            )
        distancias = distancias_euclideas(X, self.X_train)
        # argsort estable: ante empates gana el ejemplo que aparece antes
        indices = np.argsort(distancias, axis=1, kind="stable")[:, : self.k]
        return indices, np.take_along_axis(distancias, indices, axis=1)

    def votos(self, X):
        """Matriz (ejemplos x clases) con cuántos vecinos votan a cada clase."""
        indices, _ = self.vecinos(X)
        etiquetas = self.y_train[indices]  # etiqueta de cada vecino
        return np.stack([(etiquetas == c).sum(axis=1) for c in self.clases], axis=1)

    def predecir_proba(self, X):
        """Fracción de vecinos que vota a cada clase (una "confianza" sencilla)."""
        return self.votos(X) / self.k

    def predecir(self, X):
        """Clase más votada para cada fila de X.

        En caso de empate de votos gana la clase del vecino más cercano de entre
        las empatadas (más sensato que elegir siempre el dígito más pequeño).
        """
        indices, _ = self.vecinos(X)
        etiquetas = self.y_train[indices]
        votos = np.stack([(etiquetas == c).sum(axis=1) for c in self.clases], axis=1)
        maximo = votos.max(axis=1)
        predicciones = np.empty(len(etiquetas), dtype=self.y_train.dtype)
        for i, fila in enumerate(etiquetas):
            empatadas = self.clases[votos[i] == maximo[i]]
            # los vecinos están ordenados por cercanía: el primero empatado gana
            predicciones[i] = next(e for e in fila if e in empatadas)
        return predicciones
