"""Comparación del k-NN propio con modelos ya hechos de scikit-learn."""

import time

from . import SEMILLA
from .knn import ClasificadorKNN
from .metricas import exactitud, f1_macro, matriz_confusion


class _AdaptadorKNN:
    """Da al k-NN propio la misma interfaz (fit/predict) que usa scikit-learn."""

    def __init__(self, k, ponderado=False):
        self.modelo = ClasificadorKNN(k=k, ponderado=ponderado)

    def fit(self, X, y):
        self.modelo.entrenar(X, y)
        return self

    def predict(self, X):
        return self.modelo.predecir(X)


def crear_modelos(k=3):
    """Diccionario nombre -> modelo sin entrenar. Las semillas van fijadas."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import SVC

    return {
        f"k-NN propio (k={k})": _AdaptadorKNN(k),
        f"k-NN propio ponderado (k={k})": _AdaptadorKNN(k, ponderado=True),
        "Regresión logística": LogisticRegression(max_iter=2000, random_state=SEMILLA),
        "SVM (kernel RBF)": SVC(kernel="rbf", C=10, gamma="scale", random_state=SEMILLA),
        "Bosque aleatorio": RandomForestClassifier(n_estimators=200, random_state=SEMILLA),
    }


def comparar_modelos(X_train, y_train, X_test, y_test, k=3):
    """Entrena y evalúa cada modelo con los mismos datos.

    Devuelve una lista de diccionarios (nombre, exactitud, f1, fallos y los
    segundos que tarda en entrenar y en predecir), ordenada de mejor a peor.
    """
    resultados = []
    for nombre, modelo in crear_modelos(k).items():
        inicio = time.perf_counter()
        modelo.fit(X_train, y_train)
        t_entrenar = time.perf_counter() - inicio

        inicio = time.perf_counter()
        predicciones = modelo.predict(X_test)
        t_predecir = time.perf_counter() - inicio

        resultados.append({
            "nombre": nombre,
            "exactitud": exactitud(y_test, predicciones),
            "f1": f1_macro(matriz_confusion(y_test, predicciones)),
            "fallos": int((predicciones != y_test).sum()),
            "t_entrenar": t_entrenar,
            "t_predecir": t_predecir,
        })
    # sorted es estable: a igualdad de exactitud se mantiene el orden original
    return sorted(resultados, key=lambda r: -r["exactitud"])
