"""Modelos lineales de una sola neurona: perceptrón y regresión logística.

Los dos calculan z = X·w + b (una recta en 2D). Cambia cómo aprenden:
- Perceptrón (Rosenblatt, 1958): solo corrige cuando se equivoca.
- Regresión logística: pasa z por una sigmoide para obtener una probabilidad
  y baja por el gradiente de la entropía cruzada (descenso de gradiente).
Son la pieza básica de la que luego saldrá la red multicapa.
"""

import numpy as np

from .metricas import entropia_cruzada_binaria


def sigmoide(z):
    """1 / (1 + e^-z), escrita de forma numéricamente estable."""
    z = np.asarray(z, dtype=float)
    salida = np.empty_like(z)
    pos = z >= 0
    salida[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    salida[~pos] = ez / (1.0 + ez)
    return salida


def _comprobar_entrada(X, y=None):
    X = np.asarray(X, dtype=float)
    if X.ndim != 2:
        raise ValueError("X debe ser una matriz (n_ejemplos, n_caracteristicas)")
    if y is not None:
        y = np.asarray(y)
        if len(y) != len(X):
            raise ValueError("X e y deben tener el mismo número de ejemplos")
        if not set(np.unique(y)) <= {0, 1}:
            raise ValueError("Las etiquetas deben ser 0 y 1")
    return X, y


class Perceptron:
    """Perceptrón clásico con la regla de aprendizaje de Rosenblatt."""

    def __init__(self, tasa=0.1, epocas=50, semilla=42):
        self.tasa = tasa
        self.epocas = epocas
        self.semilla = semilla
        self.w = None
        self.b = 0.0
        self.historial = []  # errores (ejemplos mal clasificados) por época

    def entrenar(self, X, y):
        X, y = _comprobar_entrada(X, y)
        rng = np.random.default_rng(self.semilla)
        self.w = np.zeros(X.shape[1])
        self.b = 0.0
        self.historial = []
        for _ in range(self.epocas):
            errores = 0
            for i in rng.permutation(len(X)):
                pred = 1 if X[i] @ self.w + self.b >= 0 else 0
                fallo = y[i] - pred  # 0 si acierta, +1/-1 si falla
                if fallo:
                    # Empuja la recta hacia el lado correcto del ejemplo
                    self.w += self.tasa * fallo * X[i]
                    self.b += self.tasa * fallo
                    errores += 1
            self.historial.append(errores)
            if errores == 0:  # convergió: todos bien clasificados
                break
        return self

    def puntuacion(self, X):
        """Valor z = X·w + b (positivo -> clase 1)."""
        if self.w is None:
            raise RuntimeError("El modelo no está entrenado")
        X, _ = _comprobar_entrada(X)
        return X @ self.w + self.b

    def predecir(self, X):
        return (self.puntuacion(X) >= 0).astype(int)


class RegresionLogistica:
    """Una neurona con activación sigmoide entrenada por descenso de gradiente."""

    def __init__(self, tasa=0.5, epocas=300, l2=0.0, semilla=42):
        self.tasa = tasa
        self.epocas = epocas
        self.l2 = l2  # regularización: penaliza pesos grandes
        self.semilla = semilla
        self.w = None
        self.b = 0.0
        self.historial = []  # pérdida por época

    def entrenar(self, X, y):
        X, y = _comprobar_entrada(X, y)
        rng = np.random.default_rng(self.semilla)
        self.w = rng.normal(0, 0.01, size=X.shape[1])
        self.b = 0.0
        self.historial = []
        n = len(X)
        for _ in range(self.epocas):
            p = sigmoide(X @ self.w + self.b)
            # Gradiente de la entropía cruzada respecto a z: simplemente (p - y)
            error = p - y
            grad_w = X.T @ error / n + self.l2 * self.w
            grad_b = error.mean()
            self.w -= self.tasa * grad_w
            self.b -= self.tasa * grad_b
            perdida = entropia_cruzada_binaria(y, p) + 0.5 * self.l2 * (self.w @ self.w)
            self.historial.append(perdida)
        return self

    def probabilidades(self, X):
        """P(clase = 1 | x) para cada ejemplo."""
        if self.w is None:
            raise RuntimeError("El modelo no está entrenado")
        X, _ = _comprobar_entrada(X)
        return sigmoide(X @ self.w + self.b)

    def puntuacion(self, X):
        return self.probabilidades(X) - 0.5

    def predecir(self, X):
        return (self.probabilidades(X) >= 0.5).astype(int)
