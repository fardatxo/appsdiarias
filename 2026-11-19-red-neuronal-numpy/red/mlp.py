"""Red neuronal multicapa (MLP) con backpropagation escrita a mano.

Estructura: entrada -> [Densa -> activación] x k capas ocultas -> Densa -> salida.
- Dos clases: 1 neurona de salida con sigmoide = P(clase 1), entropía cruzada binaria.
- Más clases: una neurona por clase con softmax, entropía cruzada categórica.
Se entrena por mini-lotes con un optimizador (SGD, momentum o Adam) y puede
apartar un conjunto de validación para hacer parada temprana.

Backpropagation = regla de la cadena aplicada capa a capa, de la salida hacia
la entrada. Cada capa guarda en el forward lo que necesita para el backward.
"""

import numpy as np

from .datos import dividir
from .lineales import sigmoide
from .metricas import entropia_cruzada_binaria, entropia_cruzada_categorica
from .optimizadores import OPTIMIZADORES, crear_optimizador


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


def softmax(z):
    """Convierte cada fila de logits en probabilidades que suman 1.
    Se resta el máximo de cada fila para que exp() no se desborde."""
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


# --- Inicialización de pesos ----------------------------------------------
# Desviación típica de los pesos iniciales según el nº de entradas/salidas.
# La idea: que la varianza de las activaciones se mantenga parecida capa tras
# capa. Si es demasiado pequeña, la señal se apaga; si es grande, se satura.
INICIALIZACIONES = {
    "lecun": lambda n_in, n_out: np.sqrt(1.0 / n_in),            # la del día 2
    "xavier": lambda n_in, n_out: np.sqrt(2.0 / (n_in + n_out)),  # Glorot: tanh/sigmoide
    "he": lambda n_in, n_out: np.sqrt(2.0 / n_in),                # ReLU (anula media señal)
    "pequena": lambda n_in, n_out: 0.01,                          # mala idea a propósito
}


# --- Capas ----------------------------------------------------------------

class Densa:
    """Capa totalmente conectada: z = a_prev · W + b."""

    def __init__(self, n_entrada, n_salida, rng, inicializacion="lecun"):
        if inicializacion not in INICIALIZACIONES:
            raise ValueError(
                f"Inicialización desconocida: {inicializacion!r}. "
                f"Opciones: {', '.join(INICIALIZACIONES)}"
            )
        desviacion = INICIALIZACIONES[inicializacion](n_entrada, n_salida)
        self.W = rng.normal(0.0, desviacion, size=(n_entrada, n_salida))
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

def _comprobar_datos(X, y=None):
    """Valida X e y. Las etiquetas deben ser enteros 0..k-1 (sin huecos)."""
    X = np.asarray(X, dtype=float)
    if X.ndim != 2:
        raise ValueError("X debe ser una matriz (n_ejemplos, n_caracteristicas)")
    if y is not None:
        y = np.asarray(y)
        if len(y) != len(X):
            raise ValueError("X e y deben tener el mismo número de ejemplos")
        if len(y) == 0:
            raise ValueError("No hay ejemplos")
        clases = np.unique(y)
        if not np.issubdtype(y.dtype, np.integer) or clases.min() < 0 or (
                len(clases) > 2 and not np.array_equal(clases, np.arange(len(clases)))):
            raise ValueError("Las etiquetas deben ser enteros 0, 1, ..., k-1")
        if len(clases) <= 2 and not set(clases) <= {0, 1}:
            raise ValueError("Con dos clases las etiquetas deben ser 0 y 1")
    return X, y


class MLP:
    """Perceptrón multicapa para clasificación binaria o multiclase."""

    def __init__(self, ocultas=(16, 16), activacion="tanh", tasa=None, epocas=500,
                 tam_lote=32, l2=0.0, semilla=42, optimizador="sgd",
                 inicializacion="lecun", validacion=0.0, paciencia=None):
        ocultas = tuple(int(n) for n in ocultas)
        if any(n <= 0 for n in ocultas):
            raise ValueError("Cada capa oculta debe tener al menos 1 neurona")
        if (tasa is not None and tasa <= 0) or epocas <= 0 or tam_lote <= 0:
            raise ValueError("tasa, epocas y tam_lote deben ser positivos")
        if activacion not in ACTIVACIONES:
            raise ValueError(
                f"Activación desconocida: {activacion!r}. Opciones: {', '.join(ACTIVACIONES)}"
            )
        if optimizador not in OPTIMIZADORES:
            raise ValueError(
                f"Optimizador desconocido: {optimizador!r}. "
                f"Opciones: {', '.join(OPTIMIZADORES)}"
            )
        if inicializacion not in INICIALIZACIONES:
            raise ValueError(
                f"Inicialización desconocida: {inicializacion!r}. "
                f"Opciones: {', '.join(INICIALIZACIONES)}"
            )
        if not 0 <= validacion < 1:
            raise ValueError("validacion debe estar en [0, 1)")
        if paciencia is not None and (paciencia <= 0 or validacion == 0):
            raise ValueError("La parada temprana necesita paciencia > 0 y validacion > 0")
        self.ocultas = ocultas
        self.activacion = activacion
        self.optimizador = optimizador
        self.tasa = OPTIMIZADORES[optimizador].tasa_defecto if tasa is None else tasa
        self.epocas = epocas
        self.tam_lote = tam_lote
        self.l2 = l2
        self.semilla = semilla
        self.inicializacion = inicializacion
        self.validacion = validacion
        self.paciencia = paciencia
        self.capas = None
        self.n_salidas = 1          # 1 = binaria (sigmoide); k > 1 = softmax
        self.historial = []         # pérdida en train por época
        self.historial_val = []     # pérdida en validación por época
        self.exactitud_val = []     # exactitud en validación por época
        self.mejor_epoca = None     # época con menor pérdida de validación

    @property
    def multiclase(self):
        return self.n_salidas > 1

    # -- construcción --
    def construir(self, n_entrada, n_salidas=1):
        """Crea las capas con pesos aleatorios reproducibles."""
        rng = np.random.default_rng(self.semilla)
        self.n_salidas = n_salidas
        tamanos = (n_entrada, *self.ocultas, n_salidas)
        self.capas = []
        for i, (a, b) in enumerate(zip(tamanos[:-1], tamanos[1:])):
            self.capas.append(Densa(a, b, rng, self.inicializacion))
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
        return a if self.multiclase else a[:, 0]

    def _salida(self, X):
        """Probabilidades: (n,) con sigmoide o (n, k) con softmax."""
        z = self._logits(X)
        return softmax(z) if self.multiclase else sigmoide(z)

    def _perdida_datos(self, y, p):
        if self.multiclase:
            return entropia_cruzada_categorica(y, p)
        return entropia_cruzada_binaria(y, p)

    def _penalizacion(self):
        return 0.5 * self.l2 * sum(np.sum(c.W ** 2) for c in self.densas())

    def perdida(self, X, y):
        """Entropía cruzada + penalización L2 (sin actualizar nada)."""
        return self._perdida_datos(y, self._salida(X)) + self._penalizacion()

    def gradientes(self, X, y):
        """Forward + backward sobre un lote. Deja dW/db en cada capa densa
        y devuelve la pérdida del lote."""
        n = len(X)
        p = self._salida(X)
        # Sigmoide + entropía cruzada binaria  -> dL/dz = (p - y) / n
        # Softmax  + entropía cruzada categórica -> dL/dz = (P - Y_onehot) / n
        # (la misma fórmula: por eso se usan siempre en pareja)
        if self.multiclase:
            objetivo = np.eye(self.n_salidas)[np.asarray(y, dtype=int)]
            grad = (p - objetivo) / n
        else:
            grad = ((p - y) / n)[:, None]
        for capa in reversed(self.capas):
            grad = capa.backward(grad)
        for c in self.densas():
            c.dW += self.l2 * c.W
        return self._perdida_datos(y, p) + self._penalizacion()

    def _pares(self):
        """Lista (parámetro, gradiente) en orden fijo para el optimizador."""
        pares = []
        for c in self.densas():
            pares += [(c.W, c.dW), (c.b, c.db)]
        return pares

    def _copiar_pesos(self):
        return [(c.W.copy(), c.b.copy()) for c in self.densas()]

    def _restaurar_pesos(self, pesos):
        for c, (W, b) in zip(self.densas(), pesos):
            c.W, c.b = W.copy(), b.copy()

    # -- entrenamiento --
    def entrenar(self, X, y):
        X, y = _comprobar_datos(X, y)
        y = y.astype(int)
        n_clases = int(y.max()) + 1
        n_salidas = n_clases if n_clases > 2 else 1

        # Conjunto de validación: se aparta una parte de train que el modelo
        # NO usa para aprender, solo para vigilar si generaliza.
        X_val = y_val = None
        if self.validacion > 0:
            X, X_val, y, y_val = dividir(X, y, proporcion_test=self.validacion,
                                         semilla=self.semilla)
        y_entreno = y if n_salidas > 1 else y.astype(float)

        self.construir(X.shape[1], n_salidas)
        opt = crear_optimizador(self.optimizador, self.tasa)
        rng = np.random.default_rng(self.semilla + 1)
        self.historial, self.historial_val, self.exactitud_val = [], [], []
        self.mejor_epoca, mejor_val, mejores_pesos, sin_mejora = None, np.inf, None, 0

        for epoca in range(self.epocas):
            orden = rng.permutation(len(X))
            for inicio in range(0, len(X), self.tam_lote):
                lote = orden[inicio:inicio + self.tam_lote]
                self.gradientes(X[lote], y_entreno[lote])
                opt.paso(self._pares())  # el optimizador decide cómo moverse
            self.historial.append(self.perdida(X, y_entreno))

            if X_val is not None:
                perdida_val = self.perdida(X_val, y_val if self.multiclase
                                           else y_val.astype(float))
                self.historial_val.append(perdida_val)
                self.exactitud_val.append(float((self.predecir(X_val) == y_val).mean()))
                if perdida_val < mejor_val - 1e-6:
                    mejor_val, sin_mejora = perdida_val, 0
                    self.mejor_epoca = epoca + 1
                    mejores_pesos = self._copiar_pesos()
                else:
                    sin_mejora += 1
                # Parada temprana: si la validación lleva `paciencia` épocas sin
                # mejorar, el modelo empieza a memorizar train -> paramos.
                if self.paciencia is not None and sin_mejora >= self.paciencia:
                    break

        # Con parada temprana nos quedamos con los pesos de la mejor época
        if self.paciencia is not None and mejores_pesos is not None:
            self._restaurar_pesos(mejores_pesos)
        return self

    # -- predicción --
    def _comprobar_entrenado(self):
        if self.capas is None:
            raise RuntimeError("El modelo no está entrenado")

    def probabilidades(self, X):
        """Binaria: P(clase 1) con forma (n,). Multiclase: matriz (n, k)."""
        self._comprobar_entrenado()
        X, _ = _comprobar_datos(X)
        return self._salida(X)

    def puntuacion(self, X):
        return self.probabilidades(X) - 0.5

    def predecir(self, X):
        p = self.probabilidades(X)
        if self.multiclase:
            return p.argmax(axis=1)
        return (p >= 0.5).astype(int)


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
    X, y = _comprobar_datos(X, y)
    n_clases = int(y.max()) + 1
    y = y.astype(int) if n_clases > 2 else y.astype(float)
    if modelo.capas is None:
        modelo.construir(X.shape[1], n_clases if n_clases > 2 else 1)
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


def desviacion_activaciones(modelo, X):
    """Desviación típica de la salida de cada capa oculta (tras la activación)
    en un forward con los pesos tal como están. Sirve para ver si la señal se
    apaga (→ 0) o se satura al atravesar muchas capas."""
    modelo._comprobar_entrenado()
    a = np.asarray(X, dtype=float)
    desviaciones = []
    for capa in modelo.capas:
        a = capa.forward(a)
        if isinstance(capa, Activacion):
            desviaciones.append(float(a.std()))
    return desviaciones
