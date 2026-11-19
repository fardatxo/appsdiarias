"""Métricas de clasificación binaria implementadas con numpy."""

import numpy as np


def exactitud(y_real, y_pred):
    """Fracción de aciertos (accuracy)."""
    y_real, y_pred = np.asarray(y_real), np.asarray(y_pred)
    if len(y_real) != len(y_pred):
        raise ValueError("y_real e y_pred deben tener la misma longitud")
    if len(y_real) == 0:
        raise ValueError("No hay ejemplos")
    return float((y_real == y_pred).mean())


def matriz_confusion(y_real, y_pred):
    """Matriz 2x2: fila = clase real, columna = clase predicha.

    [[VN, FP],
     [FN, VP]]
    """
    m = np.zeros((2, 2), dtype=int)
    for r, p in zip(np.asarray(y_real), np.asarray(y_pred)):
        m[int(r), int(p)] += 1
    return m


def precision_recall_f1(y_real, y_pred):
    """Precisión, exhaustividad (recall) y F1 de la clase positiva (1)."""
    (vn, fp), (fn, vp) = matriz_confusion(y_real, y_pred)
    precision = vp / (vp + fp) if vp + fp else 0.0
    recall = vp / (vp + fn) if vp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return float(precision), float(recall), float(f1)


def entropia_cruzada_binaria(y_real, probabilidades, eps=1e-12):
    """Pérdida log-loss: castiga mucho las predicciones seguras y equivocadas."""
    p = np.clip(probabilidades, eps, 1 - eps)
    y = np.asarray(y_real, dtype=float)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def formatear_matriz(m):
    """Texto legible de la matriz de confusión."""
    return (
        "              pred 0  pred 1\n"
        f"  real 0   {m[0, 0]:>8}{m[0, 1]:>8}\n"
        f"  real 1   {m[1, 0]:>8}{m[1, 1]:>8}"
    )
