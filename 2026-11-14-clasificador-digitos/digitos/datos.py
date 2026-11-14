"""Carga y preparación de los datos."""

import numpy as np
from sklearn.datasets import load_digits

from . import SEMILLA

LADO = 8          # las imágenes son de 8x8 píxeles
PIXEL_MAX = 16.0  # cada píxel va de 0 (blanco) a 16 (negro)


def cargar_digitos():
    """Devuelve (X, y): X con una fila de 64 píxeles por imagen, y con el dígito real."""
    datos = load_digits()
    X = datos.data.astype(float)
    y = datos.target.astype(int)
    return X, y


def normalizar(X):
    """Escala los píxeles al rango [0, 1]."""
    return np.asarray(X, dtype=float) / PIXEL_MAX


def dividir_train_test(X, y, proporcion_test=0.25, semilla=SEMILLA):
    """Divide los datos en entrenamiento y test de forma estratificada.

    Estratificada = cada dígito mantiene la misma proporción en ambos conjuntos,
    para que el test no tenga por casualidad muchos "3" y pocos "7".
    Devuelve (X_train, X_test, y_train, y_test).
    """
    if not 0 < proporcion_test < 1:
        raise ValueError("proporcion_test debe estar entre 0 y 1 (sin incluirlos)")
    X = np.asarray(X)
    y = np.asarray(y)
    if len(X) != len(y):
        raise ValueError("X e y deben tener el mismo número de ejemplos")

    rng = np.random.default_rng(semilla)
    indices_train, indices_test = [], []
    for clase in np.unique(y):
        indices = np.flatnonzero(y == clase)
        rng.shuffle(indices)
        n_test = max(1, int(round(len(indices) * proporcion_test)))
        indices_test.extend(indices[:n_test])
        indices_train.extend(indices[n_test:])

    # Barajamos para que las clases no queden ordenadas
    indices_train = rng.permutation(indices_train)
    indices_test = rng.permutation(indices_test)
    return X[indices_train], X[indices_test], y[indices_train], y[indices_test]


def preparar_datos(proporcion_test=0.25, semilla=SEMILLA):
    """Atajo: carga, normaliza y divide el dataset."""
    X, y = cargar_digitos()
    return dividir_train_test(normalizar(X), y, proporcion_test, semilla)
