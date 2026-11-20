"""Red neuronal multicapa (MLP) con backpropagation escrita a mano.

Estructura: entrada -> [Densa -> activación] x k capas ocultas -> Densa -> sigmoide.
La salida es una probabilidad P(clase = 1) y se entrena minimizando la entropía
cruzada binaria con descenso de gradiente por mini-lotes.

Backpropagation = regla de la cadena aplicada capa a capa, de la salida hacia
la entrada. Cada capa guarda en el forward lo que necesita para el backward.
"""

import numpy as np

from .lineales import _comprobar_entrada, sigmoide
from .metricas import entropia_cruzada_binaria


# --- Activaciones ---------------------------------------------------------
# Cada activación es un par (f, f') donde f' se calcula a partir de la
# entrada z de la activación.

def relu(z):
    return np.maximum(0.0, z)


def relu_derivada(z):
    return (z > 0).astype(float)


def tanh_derivada(z):
    t = np.tanh(z)
    return 1.0 - t * t


def sigmoide_derivada(z):
    s = sigmoide(z)
    return s * (1.0 - s)


ACTIVACIONES = {
    "relu": (relu, relu_derivada),
    "tanh": (np.tanh, tanh_derivada),
    "sigmoide": (sigmoide, sigmoide_derivada),
}


# --- Capas ----------------------------------------------------------------

class Densa:
    """Capa totalmente conectada: z = a_prev · W + b."""

    def __init__(self, n_entrada, n_salida, rng):
        # Pesos pequeños escalados por 1/sqrt(n_entrada) (estilo Xavier):
        # así la varianza de z no explota ni se anula al apilar capas.
        self.W = rng.normal(0.0, 1.0 / np.sqrt(n_entrada), size=(n_entrada, n_salida))
        self.b = np.zeros(n_salida)
        self._entrada = None
        self.dW = np.zeros_like(self.W)
        self.db = np.zeros_like(self.b)

    def forward(self, a_prev):
        self._entrada = a_prev  # se guarda para calcular dW en el backward
        return a_prev @ self.W + self.b

    def backward(self, dz):
        """Recibe dL/dz (lote, n_salida) y devuelve dL/da_prev."""
        self.dW = self._entrada.T @ dz
        self.db = dz.sum(axis=0)
        return dz @ self.W.T


class Activacion:
    """Aplica una función no lineal elemento a elemento."""

    def __init__(self, nombre):
        if nombre not in ACTIVACIONES:
            raise ValueError(
                f"Activación desconocida: {nombre!r}. Opciones: {', '.join(ACTIVACIONES)}"
            )
        self.nombre = nombre
        self.f, self.df = ACTIVACIONES[nombre]
        self._z = None

    def forward(self, z):
        self._z = z
        return self.f(z)

    def backward(self, da):
        # Regla de la cadena: dL/dz = dL/da * f'(z)
        return da * self.df(self._z)


# --- Red ------------------------------------------------------------------

class MLP:
    """Perceptrón multicapa para clasificación binaria."""

    def __init__(self, ocultas=(16, 16), activacion="tanh", tasa=0.1, epocas=500,
                 tam_lote=32, l2=0.0, semilla=42):
        ocultas = tuple(int(n) for n in ocultas)
        if any(n <= 0 for n in ocultas):
            raise ValueError("Cada capa oculta debe tener al menos 1 neurona")
        if tasa <= 0 or epocas <= 0 or tam_lote <= 0:
            raise ValueError("tasa, epocas y tam_lote deben ser positivos")
        if activacion not in ACTIVACIONES:
            raise ValueError(
                f"Activación desconocida: {activacion!r}. Opciones: {', '.join(ACTIVACIONES)}"
            )
        self.ocultas = ocultas
        self.activacion = activacion
        self.tasa = tasa
        self.epocas = epocas
        self.tam_lote = tam_lote
        self.l2 = l2
        self.semilla = semilla
        self.capas = None
        self.historial = []  # pérdida en train por época

    # -- construcción --
    def construir(self, n_entrada):
        """Crea las capas con pesos aleatorios reproducibles."""
        rng = np.random.default_rng(self.semilla)
        tamanos = (n_entrada, *self.ocultas, 1)
        self.capas = []
        for i, (a, b) in enumerate(zip(tamanos[:-1], tamanos[1:])):
            self.capas.append(Densa(a, b, rng))
            if i < len(tamanos) - 2:  # la última capa no lleva activación oculta
                self.capas.append(Activacion(self.activacion))
        return self

    def densas(self):
        return [c for c in self.capas if isinstance(c, Densa)]

    def num_parametros(self):
        return sum(c.W.size + c.b.size for c in self.densas())

    # -- forward / backward --
    def _logits(self, X):
        a = X
        for capa in self.capas:
            a = capa.forward(a)
        return a[:, 0]  # (lote,)

    def perdida(self, X, y):
        """Entropía cruzada + penalización L2 (sin actualizar nada)."""
        p = sigmoide(self._logits(X))
        reg = 0.5 * self.l2 * sum(np.sum(c.W ** 2) for c in self.densas())
        return entropia_cruzada_binaria(y, p) + reg

    def gradientes(self, X, y):
        """Forward + backward sobre un lote. Deja dW/db en cada capa densa
        y devuelve la pérdida del lote."""
        n = len(X)
        p = sigmoide(self._logits(X))
        # Sigmoide + entropía cruzada: dL/dz de la salida es (p - y) / n
        grad = ((p - y) / n)[:, None]
        for capa in reversed(self.capas):
            grad = capa.backward(grad)
        for c in self.densas():
            c.dW += self.l2 * c.W
        reg = 0.5 * self.l2 * sum(np.sum(c.W ** 2) for c in self.densas())
        return entropia_cruzada_binaria(y, p) + reg

    # -- entrenamiento --
    def entrenar(self, X, y):
        X, y = _comprobar_entrada(X, y)
        y = y.astype(float)
        self.construir(X.shape[1])
        rng = np.random.default_rng(self.semilla + 1)
        self.historial = []
        for _ in range(self.epocas):
            orden = rng.permutation(len(X))
            for inicio in range(0, len(X), self.tam_lote):
                lote = orden[inicio:inicio + self.tam_lote]
                self.gradientes(X[lote], y[lote])
                # Descenso de gradiente: paso contrario al gradiente
                for c in self.densas():
                    c.W -= self.tasa * c.dW
                    c.b -= self.tasa * c.db
            self.historial.append(self.perdida(X, y))
        return self

    # -- predicción --
    def _comprobar_entrenado(self):
        if self.capas is None:
            raise RuntimeError("El modelo no está entrenado")

    def probabilidades(self, X):
        self._comprobar_entrenado()
        X, _ = _comprobar_entrada(X)
        return sigmoide(self._logits(X))

    def puntuacion(self, X):
        return self.probabilidades(X) - 0.5

    def predecir(self, X):
        return (self.probabilidades(X) >= 0.5).astype(int)


def comprobar_gradientes(modelo, X, y, eps=1e-5):
    """Compara el gradiente de backprop con uno numérico (diferencias centrales).

    Para cada parámetro θ: (L(θ+ε) - L(θ-ε)) / 2ε ≈ dL/dθ.
    Para cada matriz de parámetros se calcula el error relativo
    ||g_backprop - g_numérico|| / (||g_backprop|| + ||g_numérico||) y se devuelve
    el peor. Debería ser < 1e-6 si backprop está bien. (Se usan normas y no
    elemento a elemento porque con sigmoide los gradientes de las primeras capas
    son diminutos y el redondeo inflaría el error relativo de cada número suelto.)

    Ojo con ReLU: tiene un "pico" en z = 0 donde la derivada no está definida.
    Con sesgos a 0, un ejemplo cuyas entradas a una capa son todas 0 cae justo
    en el pico y la comparación falla sin que haya ningún error. Por eso se
    ponen sesgos aleatorios pequeños antes de comprobar.
    """
    X, y = _comprobar_entrada(X, y)
    y = y.astype(float)
    if modelo.capas is None:
        modelo.construir(X.shape[1])
        rng = np.random.default_rng(modelo.semilla + 2)
        for c in modelo.densas():
            c.b = rng.normal(0.0, 0.1, size=c.b.shape)
    modelo.gradientes(X, y)
    analiticos = [(c.dW.copy(), c.db.copy()) for c in modelo.densas()]

    peor = 0.0
    for capa, (dW, db) in zip(modelo.densas(), analiticos):
        for param, analitico in ((capa.W, dW), (capa.b, db)):
            numerico = np.zeros_like(param)
            it = np.nditer(param, flags=["multi_index"])
            for _ in it:
                i = it.multi_index
                original = param[i]
                param[i] = original + eps
                mas = modelo.perdida(X, y)
                param[i] = original - eps
                menos = modelo.perdida(X, y)
                param[i] = original
                numerico[i] = (mas - menos) / (2 * eps)
            denom = max(1e-8, np.linalg.norm(numerico) + np.linalg.norm(analitico))
            peor = max(peor, np.linalg.norm(numerico - analitico) / denom)
    return peor
