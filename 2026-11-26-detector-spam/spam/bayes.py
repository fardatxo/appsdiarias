"""Naive Bayes multinomial implementado a mano con numpy.

Idea: aplicar el teorema de Bayes

    P(spam | mensaje) ∝ P(spam) · P(mensaje | spam)

y suponer (de forma "ingenua", naive) que las palabras son independientes entre
sí dada la clase, de modo que

    P(mensaje | spam) = Π P(palabra_i | spam) ^ recuento_i

P(palabra | clase) se estima contando cuántas veces sale cada palabra en los
mensajes de esa clase. El suavizado de Laplace (alfa) suma un recuento ficticio
a todas las palabras para que una palabra nunca vista no dé probabilidad 0 y
"anule" todo el producto. Trabajamos con logaritmos para no multiplicar muchos
números pequeños (se irían a 0 por falta de precisión).
"""

import numpy as np


class NaiveBayesMultinomial:
    def __init__(self, alfa: float = 1.0):
        if alfa < 0:
            raise ValueError("alfa debe ser >= 0")
        self.alfa = alfa
        self.clases_: np.ndarray | None = None
        self.log_prior_: np.ndarray | None = None        # log P(clase)
        self.log_verosimilitud_: np.ndarray | None = None  # log P(palabra | clase)

    def entrenar(self, X: np.ndarray, y: np.ndarray) -> "NaiveBayesMultinomial":
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y)
        if X.shape[0] != y.shape[0]:
            raise ValueError("X e y deben tener el mismo número de filas")
        if np.any(X < 0):
            raise ValueError("Naive Bayes multinomial necesita recuentos no negativos")
        self.clases_ = np.unique(y)
        n_clases, n_palabras = len(self.clases_), X.shape[1]
        self.log_prior_ = np.zeros(n_clases)
        self.log_verosimilitud_ = np.zeros((n_clases, n_palabras))
        for k, clase in enumerate(self.clases_):
            Xk = X[y == clase]
            self.log_prior_[k] = np.log(Xk.shape[0] / X.shape[0])
            recuentos = Xk.sum(axis=0) + self.alfa
            self.log_verosimilitud_[k] = np.log(recuentos / recuentos.sum())
        return self

    def _comprobar(self):
        if self.clases_ is None:
            raise RuntimeError("El modelo no está entrenado")

    def puntuaciones(self, X: np.ndarray) -> np.ndarray:
        """log P(clase) + Σ recuento · log P(palabra | clase), sin normalizar."""
        self._comprobar()
        return np.asarray(X, dtype=np.float64) @ self.log_verosimilitud_.T + self.log_prior_

    def predecir_proba(self, X: np.ndarray) -> np.ndarray:
        """Probabilidades por clase (filas suman 1), con log-sum-exp para estabilidad."""
        s = self.puntuaciones(X)
        s -= s.max(axis=1, keepdims=True)
        p = np.exp(s)
        return p / p.sum(axis=1, keepdims=True)

    def predecir(self, X: np.ndarray) -> np.ndarray:
        return self.clases_[np.argmax(self.puntuaciones(X), axis=1)]

    def palabras_mas_indicativas(self, palabras: list[str], n: int = 10):
        """Palabras con mayor log P(w|spam) - log P(w|ham): las que más "delatan" al spam.

        Devuelve dos listas de (palabra, log-ratio): las más de spam y las más de ham.
        Solo tiene sentido con dos clases (0 = ham, 1 = spam).
        """
        self._comprobar()
        if len(self.clases_) != 2:
            raise ValueError("Solo disponible para clasificación binaria")
        ratio = self.log_verosimilitud_[1] - self.log_verosimilitud_[0]
        orden = np.argsort(ratio)
        spam = [(palabras[i], float(ratio[i])) for i in orden[::-1][:n]]
        ham = [(palabras[i], float(ratio[i])) for i in orden[:n]]
        return spam, ham
