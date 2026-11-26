"""Métricas de clasificación binaria (1 = spam = clase positiva).

En spam la exactitud engaña: si solo hay un 10 % de spam, un modelo que dice
siempre "ham" acierta el 90 %. Por eso miramos también:
  - precisión: de lo que marco como spam, ¿cuánto lo era? (falsos positivos = mensajes
    buenos que acaban en la carpeta de spam, lo que más molesta al usuario)
  - recall (sensibilidad): de todo el spam real, ¿cuánto he cazado?
  - F1: media armónica de las dos.
"""

import numpy as np


def matriz_confusion(y_real, y_pred) -> np.ndarray:
    """[[VN, FP], [FN, VP]]: filas = clase real (ham, spam), columnas = predicha."""
    y_real, y_pred = np.asarray(y_real), np.asarray(y_pred)
    m = np.zeros((2, 2), dtype=int)
    for r, p in zip(y_real, y_pred):
        m[int(r), int(p)] += 1
    return m


def _division(a: float, b: float) -> float:
    return float(a / b) if b else 0.0


def informe(y_real, y_pred) -> dict:
    m = matriz_confusion(y_real, y_pred)
    vn, fp, fn, vp = m[0, 0], m[0, 1], m[1, 0], m[1, 1]
    precision = _division(vp, vp + fp)
    recall = _division(vp, vp + fn)
    return {
        "exactitud": _division(vp + vn, m.sum()),
        "precision": precision,
        "recall": recall,
        "f1": _division(2 * precision * recall, precision + recall),
        "falsos_positivos": int(fp),
        "falsos_negativos": int(fn),
        "matriz": m,
    }


def formatear_informe(inf: dict) -> str:
    m = inf["matriz"]
    return "\n".join([
        f"  exactitud : {inf['exactitud']:.3f}",
        f"  precisión : {inf['precision']:.3f}",
        f"  recall    : {inf['recall']:.3f}",
        f"  F1        : {inf['f1']:.3f}",
        "",
        "  Matriz de confusión     pred. ham  pred. spam",
        f"    real ham            {m[0, 0]:9d}  {m[0, 1]:10d}",
        f"    real spam           {m[1, 0]:9d}  {m[1, 1]:10d}",
    ])
