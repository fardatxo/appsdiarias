"""Datasets de juguete en 2D y utilidades de preparación de datos.

Los datasets se generan con scikit-learn (no hay descargas) y siempre con
una semilla fija para que los resultados sean reproducibles.
"""

import numpy as np
from sklearn.datasets import load_digits, make_blobs, make_circles, make_moons

SEMILLA = 42

# Nombre -> (descripción, ¿es separable con una recta?)
DATASETS = {
    "blobs": ("Dos nubes de puntos bien separadas", True),
    "lunas": ("Dos medias lunas entrelazadas", False),
    "circulos": ("Un círculo dentro de otro", False),
    "xor": ("Cuatro cuadrantes: clase 1 si x·y > 0 (el clásico XOR)", False),
}


def generar(nombre, n=400, ruido=0.2, semilla=SEMILLA):
    """Genera un dataset 2D binario. Devuelve X (n, 2) e y (n,) con etiquetas 0/1."""
    if nombre == "blobs":
        X, y = make_blobs(n_samples=n, centers=[(-2, -2), (2, 2)],
                          cluster_std=1.0 + ruido, random_state=semilla)
    elif nombre == "lunas":
        X, y = make_moons(n_samples=n, noise=ruido, random_state=semilla)
    elif nombre == "circulos":
        X, y = make_circles(n_samples=n, noise=ruido / 2, factor=0.5,
                            random_state=semilla)
    elif nombre == "xor":
        rng = np.random.default_rng(semilla)
        X = rng.uniform(-1, 1, size=(n, 2))
        X += rng.normal(0, ruido / 4, size=X.shape)
        y = (X[:, 0] * X[:, 1] > 0).astype(int)
    else:
        raise ValueError(
            f"Dataset desconocido: {nombre!r}. Opciones: {', '.join(DATASETS)}"
        )
    return X.astype(float), y.astype(int)


def dividir(X, y, proporcion_test=0.25, semilla=SEMILLA):
    """División train/test estratificada hecha a mano.

    Estratificada = cada clase mantiene la misma proporción en train y en test.
    """
    if not 0 < proporcion_test < 1:
        raise ValueError("proporcion_test debe estar entre 0 y 1")
    rng = np.random.default_rng(semilla)
    idx_train, idx_test = [], []
    for clase in np.unique(y):
        idx = np.flatnonzero(y == clase)
        rng.shuffle(idx)
        corte = int(round(len(idx) * proporcion_test))
        idx_test.extend(idx[:corte])
        idx_train.extend(idx[corte:])
    idx_train = rng.permutation(idx_train)
    idx_test = rng.permutation(idx_test)
    return X[idx_train], X[idx_test], y[idx_train], y[idx_test]


class Estandarizador:
    """Resta la media y divide por la desviación típica de cada columna.

    Se ajusta SOLO con los datos de entrenamiento para no "espiar" el test.
    """

    def __init__(self):
        self.media = None
        self.desviacion = None

    def ajustar(self, X):
        self.media = X.mean(axis=0)
        self.desviacion = X.std(axis=0)
        self.desviacion[self.desviacion == 0] = 1.0  # evita dividir entre 0
        return self

    def transformar(self, X):
        if self.media is None:
            raise RuntimeError("Llama a ajustar() antes de transformar()")
        return (X - self.media) / self.desviacion

    def ajustar_transformar(self, X):
        return self.ajustar(X).transformar(X)


def preparar(nombre, n=400, ruido=0.2, semilla=SEMILLA, con_escala=False):
    """Genera, divide y estandariza un dataset. Devuelve X_train, X_test, y_train, y_test
    (y además el Estandarizador si `con_escala`, para poder guardarlo con el modelo)."""
    X, y = generar(nombre, n=n, ruido=ruido, semilla=semilla)
    X_train, X_test, y_train, y_test = dividir(X, y, semilla=semilla)
    escala = Estandarizador().ajustar(X_train)
    datos = (escala.transformar(X_train), escala.transformar(X_test), y_train, y_test)
    return (*datos, escala) if con_escala else datos


def preparar_digitos(proporcion_test=0.25, semilla=SEMILLA, con_escala=False):
    """Dataset `digits` de scikit-learn: 1797 imágenes 8×8 de dígitos 0-9.

    Cada imagen se aplana en 64 píxeles (valores 0-16). Se divide de forma
    estratificada y se estandariza con la media/desviación de train.
    Devuelve X_train, X_test, y_train, y_test (y el Estandarizador si `con_escala`).
    """
    X, y = cargar_digitos_crudos()
    X_train, X_test, y_train, y_test = dividir(X, y, proporcion_test, semilla)
    escala = Estandarizador().ajustar(X_train)
    datos = (escala.transformar(X_train), escala.transformar(X_test), y_train, y_test)
    return (*datos, escala) if con_escala else datos


def cargar_digitos_crudos():
    """Imágenes de `digits` sin estandarizar (píxeles 0-16) y sus etiquetas."""
    digitos = load_digits()
    return digitos.data.astype(float), digitos.target.astype(int)


def dividir_digitos_crudos(proporcion_test=0.25, semilla=SEMILLA):
    """La misma división que `preparar_digitos`, pero sin estandarizar
    (para enseñar las imágenes de test tal cual o pasarlas a un modelo guardado)."""
    X, y = cargar_digitos_crudos()
    return dividir(X, y, proporcion_test, semilla)


# Caracteres de un dígito dibujado en texto, de más claro (0) a más oscuro (16)
TINTA = " .:-=+*#%@"


def leer_dibujo(texto):
    """Convierte un dígito dibujado en 8 líneas de texto en un vector de 64 píxeles.

    Cada carácter de TINTA es un nivel de intensidad (' ' o '.' claros, '@' o
    '#' oscuros); cualquier otro carácter que no sea espacio cuenta como '#'.
    Las líneas cortas se rellenan con espacios. Si hay más de 8 líneas, se
    quitan las vacías del principio y del final (una fila en blanco dentro de
    las 8 sí cuenta: es parte del dibujo).
    """
    lineas = texto.splitlines()
    while len(lineas) > 8 and not lineas[0].strip():
        lineas.pop(0)
    while len(lineas) > 8 and not lineas[-1].strip():
        lineas.pop()
    if len(lineas) != 8 or any(len(linea) > 8 for linea in lineas):
        raise ValueError("El dibujo debe tener exactamente 8 líneas de como máximo 8 caracteres")
    pixeles = []
    for linea in lineas:
        for c in linea.ljust(8):
            nivel = TINTA.index(c) if c in TINTA else TINTA.index("#")
            pixeles.append(round(nivel * 16 / (len(TINTA) - 1)))
    return np.array(pixeles, dtype=float)


def dibujo_ascii(pixeles):
    """Inversa aproximada de leer_dibujo: 64 píxeles (0-16) -> 8 líneas de texto."""
    pixeles = np.asarray(pixeles, dtype=float).reshape(8, 8)
    niveles = np.clip(np.round(pixeles / 16 * (len(TINTA) - 1)), 0, len(TINTA) - 1)
    return "\n".join("".join(TINTA[int(n)] for n in fila) for fila in niveles)
