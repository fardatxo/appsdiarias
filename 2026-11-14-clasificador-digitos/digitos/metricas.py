"""Métricas de evaluación calculadas a mano."""

import numpy as np


def exactitud(y_real, y_pred):
    """Fracción de predicciones correctas (accuracy), entre 0 y 1."""
    y_real = np.asarray(y_real)
    y_pred = np.asarray(y_pred)
    if y_real.shape != y_pred.shape:
        raise ValueError("y_real e y_pred deben tener la misma forma")
    if y_real.size == 0:
        raise ValueError("No hay ejemplos que evaluar")
    return float(np.mean(y_real == y_pred))


def matriz_confusion(y_real, y_pred, clases=None):
    """Matriz donde la fila es la clase real y la columna la clase predicha.

    La diagonal son los aciertos; todo lo que queda fuera son errores, y la
    posición dice qué dígito se confundió con cuál.
    """
    y_real = np.asarray(y_real)
    y_pred = np.asarray(y_pred)
    if clases is None:
        clases = np.unique(np.concatenate([y_real, y_pred]))
    posicion = {c: i for i, c in enumerate(clases)}
    matriz = np.zeros((len(clases), len(clases)), dtype=int)
    for real, pred in zip(y_real, y_pred):
        matriz[posicion[real], posicion[pred]] += 1
    return matriz


def formatear_matriz(matriz, clases):
    """Devuelve la matriz de confusión como texto alineado para la terminal."""
    ancho = max(3, len(str(matriz.max())) + 1)
    lineas = ["real\\pred " + "".join(f"{c:>{ancho}}" for c in clases)]
    for clase, fila in zip(clases, matriz):
        celdas = "".join(f"{(v if v else '.'):>{ancho}}" for v in fila)
        lineas.append(f"{clase:>9} {celdas}")
    return "\n".join(lineas)
