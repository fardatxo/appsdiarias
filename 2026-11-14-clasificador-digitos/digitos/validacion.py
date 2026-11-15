"""Validación cruzada hecha a mano para elegir k sin mirar el conjunto de test.

Idea: el entrenamiento se parte en N trozos ("pliegues"). Por turnos, uno hace
de examen y los demás de entrenamiento; la nota final es la media de los N
exámenes. Así se puede comparar valores de k y dejar el test intacto para la
evaluación final.
"""

import numpy as np

from . import SEMILLA
from .knn import ClasificadorKNN
from .metricas import exactitud


def pliegues_estratificados(y, n_pliegues=5, semilla=SEMILLA):
    """Reparte los índices de y en n_pliegues grupos con las clases equilibradas."""
    y = np.asarray(y)
    if n_pliegues < 2:
        raise ValueError("Hacen falta al menos 2 pliegues")
    if n_pliegues > len(y):
        raise ValueError("No puede haber más pliegues que ejemplos")
    rng = np.random.default_rng(semilla)
    pliegues = [[] for _ in range(n_pliegues)]
    siguiente = 0
    for clase in np.unique(y):
        indices = np.flatnonzero(y == clase)
        rng.shuffle(indices)
        # se reparten como cartas, continuando donde se quedó la clase anterior
        for indice in indices:
            pliegues[siguiente % n_pliegues].append(indice)
            siguiente += 1
    return [np.array(sorted(p), dtype=int) for p in pliegues]


def validacion_cruzada_knn(X, y, k, n_pliegues=5, ponderado=False, semilla=SEMILLA):
    """Exactitud de un k-NN en cada pliegue (array de n_pliegues valores)."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y)
    pliegues = pliegues_estratificados(y, n_pliegues, semilla)
    notas = []
    for i, examen in enumerate(pliegues):
        resto = np.concatenate([p for j, p in enumerate(pliegues) if j != i])
        modelo = ClasificadorKNN(k=k, ponderado=ponderado).entrenar(X[resto], y[resto])
        notas.append(exactitud(y[examen], modelo.predecir(X[examen])))
    return np.array(notas)


def elegir_k(X, y, valores_k, n_pliegues=5, ponderado=False, semilla=SEMILLA):
    """Devuelve (mejor_k, medias): la exactitud media de validación de cada k.

    En caso de empate gana el k más pequeño (el primero de la lista).
    """
    medias = [
        float(validacion_cruzada_knn(X, y, k, n_pliegues, ponderado, semilla).mean())
        for k in valores_k
    ]
    return valores_k[int(np.argmax(medias))], medias
