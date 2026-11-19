"""Datasets de juguete en 2D y utilidades de preparación de datos.

Los datasets se generan con scikit-learn (no hay descargas) y siempre con
una semilla fija para que los resultados sean reproducibles.
"""

import numpy as np
from sklearn.datasets import make_blobs, make_circles, make_moons

SEMILLA = 42

# Nombre -> (descripción, ¿es separable con una recta?)
DATASETS = {
    "blobs": ("Dos nubes de puntos bien separadas", True),
    "lunas": ("Dos medias lunas entrelazadas", False),
    "circulos": ("Un círculo dentro de otro", False),
    "xor": ("Cuatro cuadrantes: clase 1 si x·y > 0 (el clásico XOR)", False),
}


def generar(nombre, n=400, ruido=0.2, semilla=SEMILLA):
    """Genera un dataset 2D binario. Devuelve X (n, 2) e y (n,) con etiquetas 0/1."""
    if nombre == "blobs":
        X, y = make_blobs(n_samples=n, centers=[(-2, -2), (2, 2)],
                          cluster_std=1.0 + ruido, random_state=semilla)
    elif nombre == "lunas":
        X, y = make_moons(n_samples=n, noise=ruido, random_state=semilla)
    elif nombre == "circulos":
        X, y = make_circles(n_samples=n, noise=ruido / 2, factor=0.5,
                            random_state=semilla)
    elif nombre == "xor":
        rng = np.random.default_rng(semilla)
        X = rng.uniform(-1, 1, size=(n, 2))
        X += rng.normal(0, ruido / 4, size=X.shape)
        y = (X[:, 0] * X[:, 1] > 0).astype(int)
    else:
        raise ValueError(
            f"Dataset desconocido: {nombre!r}. Opciones: {', '.join(DATASETS)}"
        )
    return X.astype(float), y.astype(int)


def dividir(X, y, proporcion_test=0.25, semilla=SEMILLA):
    """División train/test estratificada hecha a mano.

    Estratificada = cada clase mantiene la misma proporción en train y en test.
    """
    if not 0 < proporcion_test < 1:
        raise ValueError("proporcion_test debe estar entre 0 y 1")
    rng = np.random.default_rng(semilla)
    idx_train, idx_test = [], []
    for clase in np.unique(y):
        idx = np.flatnonzero(y == clase)
        rng.shuffle(idx)
        corte = int(round(len(idx) * proporcion_test))
        idx_test.extend(idx[:corte])
        idx_train.extend(idx[corte:])
    idx_train = rng.permutation(idx_train)
    idx_test = rng.permutation(idx_test)
    return X[idx_train], X[idx_test], y[idx_train], y[idx_test]


class Estandarizador:
    """Resta la media y divide por la desviación típica de cada columna.

    Se ajusta SOLO con los datos de entrenamiento para no "espiar" el test.
    """

    def __init__(self):
        self.media = None
        self.desviacion = None

    def ajustar(self, X):
        self.media = X.mean(axis=0)
        self.desviacion = X.std(axis=0)
        self.desviacion[self.desviacion == 0] = 1.0  # evita dividir entre 0
        return self

    def transformar(self, X):
        if self.media is None:
            raise RuntimeError("Llama a ajustar() antes de transformar()")
        return (X - self.media) / self.desviacion

    def ajustar_transformar(self, X):
        return self.ajustar(X).transformar(X)


def preparar(nombre, n=400, ruido=0.2, semilla=SEMILLA):
    """Genera, divide y estandariza un dataset. Devuelve X_train, X_test, y_train, y_test."""
    X, y = generar(nombre, n=n, ruido=ruido, semilla=semilla)
    X_train, X_test, y_train, y_test = dividir(X, y, semilla=semilla)
    escala = Estandarizador().ajustar(X_train)
    return escala.transformar(X_train), escala.transformar(X_test), y_train, y_test
