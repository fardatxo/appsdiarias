"""Combinaciones de representación × modelo y la tabla que las compara.

Separar "cómo convierto el texto en números" (representación) de "qué modelo
aprende con esos números" permite probar todas las combinaciones con el mismo
código y ver qué aporta cada pieza.
"""

import time

import numpy as np

from .bayes import NaiveBayesMultinomial
from .logistica import RegresionLogistica
from .metricas import informe
from .vectorizador import BolsaDePalabras, VectorizadorTfIdf

# Nombre -> (descripción, función que crea un vectorizador nuevo sin entrenar)
REPRESENTACIONES = {
    "bolsa": ("recuentos de palabras",
              lambda: BolsaDePalabras()),
    "tfidf": ("TF-IDF de palabras",
              lambda: VectorizadorTfIdf(sublineal=True)),
    "tfidf-bigramas": ("TF-IDF de palabras + bigramas",
                       lambda: VectorizadorTfIdf(sublineal=True, ngramas=(1, 2))),
    "tfidf-caracteres": ("TF-IDF de n-gramas de caracteres (2-4)",
                         lambda: VectorizadorTfIdf(sublineal=True, analizador="caracter",
                                                   ngramas=(2, 4))),
}

MODELOS = {
    "bayes": ("Naive Bayes multinomial", lambda alfa, C: NaiveBayesMultinomial(alfa=alfa)),
    "logistica": ("Regresión logística (L2)", lambda alfa, C: RegresionLogistica(C=C)),
}


def crear(representacion: str, modelo: str, alfa: float = 1.0, C: float = 10.0):
    """Devuelve (vectorizador, modelo) sin entrenar. Lanza ValueError si no existen."""
    if representacion not in REPRESENTACIONES:
        raise ValueError(f"Representación desconocida: {representacion!r}. "
                         f"Opciones: {', '.join(REPRESENTACIONES)}")
    if modelo not in MODELOS:
        raise ValueError(f"Modelo desconocido: {modelo!r}. Opciones: {', '.join(MODELOS)}")
    return REPRESENTACIONES[representacion][1](), MODELOS[modelo][1](alfa, C)


def entrenar(textos, y, representacion="bolsa", modelo="bayes", alfa=1.0, C=10.0):
    """Ajusta vectorizador y modelo con los textos dados. Devuelve (vec, modelo)."""
    vec, mod = crear(representacion, modelo, alfa=alfa, C=C)
    mod.entrenar(vec.ajustar_transformar(textos), y)
    return vec, mod


def comparar(tx_train, y_train, tx_test, y_test, alfa=1.0, C=10.0, tx_test_erratas=None):
    """Entrena todas las combinaciones y devuelve una fila (dict) por cada una.

    Si se pasa tx_test_erratas (el test con erratas extra), añade también la F1
    en esos mensajes "estropeados" para medir la robustez.
    """
    filas = []
    for nombre_repr in REPRESENTACIONES:
        for nombre_mod in MODELOS:
            inicio = time.perf_counter()
            vec, mod = entrenar(tx_train, y_train, nombre_repr, nombre_mod, alfa=alfa, C=C)
            segundos = time.perf_counter() - inicio
            inf = informe(y_test, mod.predecir(vec.transformar(tx_test)))
            fila = {
                "representacion": nombre_repr,
                "modelo": nombre_mod,
                "terminos": len(vec.vocabulario),
                "segundos": segundos,
                **{k: inf[k] for k in ("exactitud", "precision", "recall", "f1",
                                       "falsos_positivos", "falsos_negativos")},
            }
            if tx_test_erratas is not None:
                pred = mod.predecir(vec.transformar(tx_test_erratas))
                fila["f1_erratas"] = informe(y_test, pred)["f1"]
            filas.append(fila)
    return filas


def formatear_tabla(filas) -> str:
    """Tabla de texto alineada, ordenada como se generó."""
    con_erratas = "f1_erratas" in filas[0]
    cab = (f"{'representación':18s} {'modelo':10s} {'términos':>8s} {'exact.':>7s} "
           f"{'prec.':>6s} {'recall':>6s} {'F1':>6s} {'FP':>3s} {'FN':>3s}")
    if con_erratas:
        cab += f" {'F1 errat.':>9s}"
    cab += f" {'tiempo':>7s}"
    lineas = [cab, "-" * len(cab)]
    mejor_f1 = max(f["f1"] for f in filas)
    for f in filas:
        linea = (f"{f['representacion']:18s} {f['modelo']:10s} {f['terminos']:8d} "
                 f"{f['exactitud']:7.3f} {f['precision']:6.3f} {f['recall']:6.3f} "
                 f"{f['f1']:6.3f} {f['falsos_positivos']:3d} {f['falsos_negativos']:3d}")
        if con_erratas:
            linea += f" {f['f1_erratas']:9.3f}"
        linea += f" {f['segundos']:6.2f}s"
        if np.isclose(f["f1"], mejor_f1):
            linea += "  ← mejor F1"
        lineas.append(linea)
    return "\n".join(lineas)


def verificar_con_sklearn(tx_train, y_train, tx_test, C=10.0) -> dict:
    """Compara nuestras piezas con las de scikit-learn y devuelve las diferencias
    máximas (deberían ser ~0): matriz TF-IDF, probabilidades de la regresión logística
    y precisión de la clasificación (fracción de predicciones iguales)."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression

    vec = VectorizadorTfIdf(sublineal=True)
    X_train = vec.ajustar_transformar(tx_train)
    X_test = vec.transformar(tx_test)
    # Le damos a sklearn nuestro propio analizador y vocabulario: así solo comparamos
    # la parte de TF-IDF (idf suavizado + tf sublineal + norma L2).
    sk_vec = TfidfVectorizer(analyzer=vec.terminos, vocabulary=vec.vocabulario,
                             sublinear_tf=True).fit(tx_train)
    dif_tfidf = float(np.abs(sk_vec.transform(tx_test).toarray() - X_test).max())

    nuestro = RegresionLogistica(C=C, max_iter=20000, tolerancia=1e-8).entrenar(X_train, y_train)
    suyo = LogisticRegression(C=C, tol=1e-10, max_iter=10000).fit(X_train, y_train)
    p_nuestra = nuestro.predecir_proba(X_test)[:, 1]
    p_suya = suyo.predict_proba(X_test)[:, 1]
    return {
        "tfidf_dif_max": dif_tfidf,
        "logistica_proba_dif_max": float(np.abs(p_nuestra - p_suya).max()),
        "logistica_pesos_dif_max": float(np.abs(nuestro.w_ - suyo.coef_[0]).max()),
        "logistica_predicciones_iguales": float(np.mean(nuestro.predecir(X_test)
                                                        == suyo.predict(X_test))),
        "logistica_iteraciones": nuestro.iteraciones_,
    }
