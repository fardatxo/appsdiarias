"""Regresión logística binaria con descenso de gradiente y regularización L2, en numpy.

A diferencia de Naive Bayes (que cuenta), la regresión logística APRENDE un peso
por término minimizando un error:

    z = X · w + b                      (puntuación lineal)
    p = sigmoide(z) = 1 / (1 + e^-z)   (probabilidad de spam)

    J(w, b) = media(-y·log p - (1-y)·log(1-p))  +  ||w||² / (2·C·n)

El primer término es la entropía cruzada (log-loss): castiga mucho estar muy
seguro y equivocarse. El segundo es la regularización L2: castiga pesos grandes
para no memorizar el train. C es el mismo parámetro que en scikit-learn (C grande
= poca regularización), por eso dividimos entre C·n: así el mínimo de J es el
mismo que el de LogisticRegression(C=C) y podemos comparar resultados.

El gradiente es sorprendentemente sencillo:
    dJ/dw = Xᵀ (p - y) / n  +  w / (C·n)
    dJ/db = media(p - y)          (el sesgo no se regulariza)
y en cada paso movemos w y b un poquito en contra del gradiente. Usamos el
"momento" de Nesterov para acelerar: el paso recuerda la dirección anterior,
como una bola que rueda cuesta abajo.
"""

import numpy as np


def sigmoide(z: np.ndarray) -> np.ndarray:
    """1 / (1 + e^-z) estable: evita overflow con z muy negativos."""
    z = np.asarray(z, dtype=np.float64)
    resultado = np.empty_like(z)
    pos = z >= 0
    resultado[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    resultado[~pos] = ez / (1.0 + ez)
    return resultado


class RegresionLogistica:
    def __init__(self, C: float = 1.0, tasa: float | None = None, momento: float = 0.9,
                 max_iter: int = 5000, tolerancia: float = 1e-6):
        if C <= 0:
            raise ValueError("C debe ser > 0")
        if tasa is not None and tasa <= 0:
            raise ValueError("la tasa de aprendizaje debe ser > 0")
        self.C = C
        self.tasa = tasa              # tamaño del paso (None = automático)
        self.momento = momento        # 0 = descenso de gradiente simple
        self.max_iter = max_iter
        self.tolerancia = tolerancia  # para cuando el gradiente es casi 0
        self.w_: np.ndarray | None = None
        self.b_: float = 0.0
        self.historial_: list[float] = []  # pérdida J en cada iteración
        self.iteraciones_: int = 0
        self.clases_ = np.array([0, 1])

    def _perdida_y_gradiente(self, X, y, w, b):
        n = X.shape[0]
        lam = 1.0 / (self.C * n)
        z = X @ w + b
        p = sigmoide(z)
        # log(1 + e^z) - y·z es la log-loss escrita de forma numéricamente estable.
        perdida = np.mean(np.logaddexp(0.0, z) - y * z) + 0.5 * lam * (w @ w)
        error = p - y
        return perdida, X.T @ error / n + lam * w, float(error.mean())

    def tasa_automatica(self, X: np.ndarray) -> float:
        """Paso seguro = 1 / L, donde L es la "curvatura" máxima de J.

        La sigmoide tiene derivada <= 1/4, así que L <= σ_max(X)² / (4n) + 1/(C·n),
        con σ_max el mayor valor singular de X (la columna de unos del sesgo suma 1).
        Un paso mayor que 1/L puede hacer que la pérdida oscile o explote; uno mucho
        menor solo hace que tarde más.
        """
        n = X.shape[0]
        sigma = np.linalg.norm(X, 2) if X.size else 0.0
        L = (sigma ** 2 + n) / (4 * n) + 1.0 / (self.C * n)
        return 1.0 / L

    def entrenar(self, X: np.ndarray, y: np.ndarray) -> "RegresionLogistica":
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        if X.shape[0] != y.shape[0]:
            raise ValueError("X e y deben tener el mismo número de filas")
        if not np.all(np.isin(y, (0, 1))):
            raise ValueError("y debe contener solo 0 (ham) y 1 (spam)")
        tasa = self.tasa if self.tasa is not None else self.tasa_automatica(X)
        self.tasa_ = tasa
        w = np.zeros(X.shape[1])
        b = 0.0
        vel_w = np.zeros_like(w)
        vel_b = 0.0
        self.historial_ = []
        for it in range(1, self.max_iter + 1):
            # Nesterov: calculamos el gradiente en el punto al que nos llevaría el momento.
            w_adelantado = w + self.momento * vel_w
            b_adelantado = b + self.momento * vel_b
            perdida, grad_w, grad_b = self._perdida_y_gradiente(X, y, w_adelantado, b_adelantado)
            self.historial_.append(float(perdida))
            vel_w = self.momento * vel_w - tasa * grad_w
            vel_b = self.momento * vel_b - tasa * grad_b
            w = w + vel_w
            b = b + vel_b
            if np.sqrt(grad_w @ grad_w + grad_b ** 2) < self.tolerancia:
                break
        self.w_, self.b_, self.iteraciones_ = w, b, it
        return self

    def _comprobar(self):
        if self.w_ is None:
            raise RuntimeError("El modelo no está entrenado")

    def puntuaciones(self, X: np.ndarray) -> np.ndarray:
        """z = X·w + b (el "logit"): > 0 significa más probable spam que ham."""
        self._comprobar()
        return np.asarray(X, dtype=np.float64) @ self.w_ + self.b_

    def predecir_proba(self, X: np.ndarray) -> np.ndarray:
        """Matriz (n, 2) con [P(ham), P(spam)], igual que Naive Bayes."""
        p = sigmoide(self.puntuaciones(X))
        return np.column_stack([1.0 - p, p])

    def predecir(self, X: np.ndarray) -> np.ndarray:
        return (self.puntuaciones(X) >= 0).astype(int)

    def palabras_mas_indicativas(self, palabras: list[str], n: int = 10):
        """Términos con el peso más positivo (spam) y más negativo (ham)."""
        self._comprobar()
        orden = np.argsort(self.w_)
        spam = [(palabras[i], float(self.w_[i])) for i in orden[::-1][:n]]
        ham = [(palabras[i], float(self.w_[i])) for i in orden[:n]]
        return spam, ham
