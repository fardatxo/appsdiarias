"""Evaluar en serio (día 3): validación cruzada, búsqueda de hiperparámetros,
curvas ROC y precisión-recall, AUC y elección del umbral. Todo a mano con numpy.

¿Por qué no basta con un train/test?
  - Con 300 mensajes de test, 2 o 3 aciertos de más o de menos mueven la F1 un punto:
    una sola división es una medida con mucho "ruido". La validación cruzada repite
    el experimento k veces con particiones distintas y da una media y una desviación.
  - Si eligiéramos alfa o C mirando el test, el test dejaría de ser "datos nunca
    vistos" y la métrica saldría optimista. Por eso los hiperparámetros (y el umbral)
    se eligen con validación cruzada SOLO dentro del train, y el test se usa una vez
    al final.

¿Por qué curvas?
  Un clasificador probabilístico no dice "spam / ham", dice P(spam). El 0.5 es un
  umbral arbitrario: subiéndolo marcamos menos mensajes como spam (más precisión,
  menos recall) y bajándolo al revés. Las curvas ROC y PR muestran TODOS los umbrales
  a la vez, y su área (AUC, precisión media) resume lo bien que el modelo ORDENA los
  mensajes, independientemente del umbral.
"""

import numpy as np

from .experimentos import MODELOS, entrenar
from .metricas import informe


# --- Validación cruzada ----------------------------------------------------

def pliegues_estratificados(y: np.ndarray, k: int = 5, semilla: int = 0):
    """Reparte los índices en k pliegues con la misma proporción de spam en cada uno.

    Devuelve una lista de k pares (idx_train, idx_validacion): en la vuelta i se
    entrena con todos los pliegues menos el i y se valida con el i. Cada mensaje
    se usa exactamente una vez para validar.
    """
    y = np.asarray(y)
    if k < 2:
        raise ValueError("k debe ser al menos 2")
    if np.bincount(y).min() < k:
        raise ValueError(f"Hay menos ejemplos de una clase que pliegues (k = {k})")
    rng = np.random.default_rng(semilla)
    pliegue_de = np.empty(len(y), dtype=int)
    for clase in np.unique(y):
        idx = np.flatnonzero(y == clase)
        rng.shuffle(idx)
        # Asignación en "rueda": 0, 1, …, k-1, 0, 1, … -> tamaños que difieren como mucho en 1.
        pliegue_de[idx] = np.arange(len(idx)) % k
    todos = np.arange(len(y))
    return [(todos[pliegue_de != i], todos[pliegue_de == i]) for i in range(k)]


def validacion_cruzada(textos, y, representacion="bolsa", modelo="bayes", alfa=1.0, C=10.0,
                       k=5, semilla=0) -> dict:
    """Entrena k veces y devuelve las métricas por pliegue, su media y desviación,
    y las probabilidades "fuera de pliegue" (out-of-fold): para cada mensaje, la
    P(spam) que dio un modelo que NO lo vio al entrenar. Esas probabilidades sirven
    para dibujar curvas y elegir el umbral sin tocar el test."""
    y = np.asarray(y)
    proba_oof = np.zeros(len(y))
    por_pliegue = []
    for idx_tr, idx_va in pliegues_estratificados(y, k, semilla):
        vec, mod = entrenar([textos[i] for i in idx_tr], y[idx_tr], representacion, modelo,
                            alfa=alfa, C=C)
        X_va = vec.transformar([textos[i] for i in idx_va])
        proba_oof[idx_va] = mod.predecir_proba(X_va)[:, 1]
        por_pliegue.append(informe(y[idx_va], mod.predecir(X_va)))
    claves = ("exactitud", "precision", "recall", "f1")
    return {
        "por_pliegue": por_pliegue,
        "media": {c: float(np.mean([p[c] for p in por_pliegue])) for c in claves},
        "desviacion": {c: float(np.std([p[c] for p in por_pliegue])) for c in claves},
        "proba_oof": proba_oof,
    }


# Valores que se prueban por defecto (en escala logarítmica: lo que importa es el orden
# de magnitud, no si C vale 10 u 11).
VALORES_POR_DEFECTO = {
    "bayes": [0.01, 0.03, 0.1, 0.3, 1.0, 3.0],
    "logistica": [0.3, 1.0, 3.0, 10.0, 30.0, 100.0],
}


def buscar_hiperparametro(textos, y, representacion="tfidf", modelo="logistica", valores=None,
                          k=5, semilla=0, metrica="f1"):
    """Búsqueda en rejilla del hiperparámetro del modelo (alfa en Bayes, C en logística)
    con validación cruzada. Devuelve (filas, mejor_valor); cada fila tiene el valor
    probado y la media/desviación de las métricas."""
    if modelo not in MODELOS:
        raise ValueError(f"Modelo desconocido: {modelo!r}")
    valores = list(valores) if valores else VALORES_POR_DEFECTO[modelo]
    filas = []
    for v in valores:
        params = {"alfa": v} if modelo == "bayes" else {"C": v}
        r = validacion_cruzada(textos, y, representacion, modelo, k=k, semilla=semilla, **params)
        filas.append({"valor": v, "media": r["media"], "desviacion": r["desviacion"]})
    # A igualdad de métrica, preferimos el modelo más sencillo: más suavizado (alfa
    # grande) o más regularización (C pequeño). Es la "navaja de Occam".
    mejor = max(filas, key=lambda f: (round(f["media"][metrica], 6),
                                      f["valor"] if modelo == "bayes" else -f["valor"]))
    return filas, mejor["valor"]


# --- Curvas ROC y precisión-recall ------------------------------------------

def _recuentos_por_umbral(y, puntuaciones):
    """Ordena por puntuación de mayor a menor y, para cada umbral distinto, cuenta
    cuántos verdaderos y falsos positivos habría marcando como spam todo lo que
    está por encima. Es el truco que hace las curvas baratas: una sola pasada."""
    y = np.asarray(y, dtype=int)
    s = np.asarray(puntuaciones, dtype=np.float64)
    orden = np.argsort(-s, kind="mergesort")
    s, y = s[orden], y[orden]
    # Posiciones donde cambia la puntuación: los empates se tratan como un bloque.
    cortes = np.r_[np.flatnonzero(np.diff(s)), len(s) - 1]
    vp = np.cumsum(y)[cortes]
    fp = (cortes + 1) - vp
    return vp, fp, s[cortes]


def curva_roc(y, puntuaciones):
    """ROC: tasa de falsos positivos (ham marcado como spam) en x, tasa de verdaderos
    positivos (= recall) en y, para todos los umbrales. Empieza en (0, 0)."""
    vp, fp, umbrales = _recuentos_por_umbral(y, puntuaciones)
    n_pos, n_neg = vp[-1], fp[-1]
    if n_pos == 0 or n_neg == 0:
        raise ValueError("La curva ROC necesita ejemplos de las dos clases")
    tfp = np.r_[0.0, fp / n_neg]
    tvp = np.r_[0.0, vp / n_pos]
    return tfp, tvp, np.r_[np.inf, umbrales]


def area_bajo_curva(x, y) -> float:
    """Área por la regla del trapecio (x debe ir ordenado de menor a mayor)."""
    x, y = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
    return float(np.sum((x[1:] - x[:-1]) * (y[1:] + y[:-1]) / 2))


def auc_roc(y, puntuaciones) -> float:
    """AUC-ROC = probabilidad de que un spam elegido al azar tenga más puntuación que
    un ham elegido al azar. 0.5 = moneda al aire, 1.0 = orden perfecto."""
    tfp, tvp, _ = curva_roc(y, puntuaciones)
    return area_bajo_curva(tfp, tvp)


def curva_precision_recall(y, puntuaciones):
    """Precisión y recall para cada umbral, de umbral alto (poco recall) a bajo.

    Con clases desequilibradas la PR es más informativa que la ROC: la ROC divide
    los FP entre TODOS los ham (muchos), así que unos pocos FP casi no se notan; la
    precisión, en cambio, los compara con lo que marcamos como spam."""
    vp, fp, umbrales = _recuentos_por_umbral(y, puntuaciones)
    if vp[-1] == 0:
        raise ValueError("La curva PR necesita al menos un ejemplo positivo")
    precision = vp / (vp + fp)
    recall = vp / vp[-1]
    return precision, recall, umbrales


def precision_media(y, puntuaciones) -> float:
    """Average precision (AP): Σ (R_n − R_{n−1}) · P_n, el área bajo la curva PR en
    "escalones" (la misma definición que scikit-learn, sin interpolar)."""
    precision, recall, _ = curva_precision_recall(y, puntuaciones)
    return float(np.sum(np.diff(np.r_[0.0, recall]) * precision))


# --- Elección del umbral -----------------------------------------------------

def elegir_umbral(y, proba, precision_minima=None):
    """Elige el umbral de P(spam) con las probabilidades de validación.

    - precision_minima=None: el umbral que maximiza la F1.
    - precision_minima=0.99 (por ejemplo): el umbral con MÁS recall entre los que
      consiguen al menos esa precisión. Es lo que querría un usuario: "prefiero que
      se me cuele algo de spam a perder un mensaje bueno". Si ningún umbral la
      alcanza, se devuelve el de mayor precisión.

    Devuelve (umbral, info) con la precisión, recall y F1 esperados en validación.
    El umbral devuelto se aplica como "P(spam) >= umbral -> spam".
    """
    precision, recall, umbrales = curva_precision_recall(y, proba)
    f1 = np.divide(2 * precision * recall, precision + recall,
                   out=np.zeros_like(precision), where=(precision + recall) > 0)
    if precision_minima is None:
        i = int(np.argmax(f1))
    else:
        validos = np.flatnonzero(precision >= precision_minima)
        i = int(validos[np.argmax(recall[validos])]) if len(validos) else int(np.argmax(precision))
    umbral = float(umbrales[i])
    return umbral, {"precision": float(precision[i]), "recall": float(recall[i]),
                    "f1": float(f1[i])}


def aplicar_umbral(proba, umbral: float) -> np.ndarray:
    return (np.asarray(proba) >= umbral).astype(int)
