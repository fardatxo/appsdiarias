"""Optimizadores: reglas para actualizar los pesos a partir del gradiente.

Todos reciben una lista de pares (parámetro, gradiente) y modifican los
parámetros *en el sitio*. Guardan su estado (velocidad, medias) por posición
en la lista, así que hay que pasar siempre los parámetros en el mismo orden.

- SGD: θ ← θ − η·g. Simple, pero avanza lento por valles alargados.
- Momentum: acumula una "velocidad" v ← β·v − η·g; θ ← θ + v. Como una bola
  que rueda: coge inercia en la dirección buena y amortigua los zigzags.
- Adam: combina momentum (media de g) con un paso adaptado a cada peso
  (dividiendo por la raíz de la media de g²). Corrige el sesgo inicial de esas
  medias, que empiezan en 0. Suele funcionar bien con η = 0.01 o 0.001.
"""

import numpy as np


class SGD:
    nombre = "sgd"
    tasa_defecto = 0.1

    def __init__(self, tasa=None):
        self.tasa = self.tasa_defecto if tasa is None else float(tasa)
        if self.tasa <= 0:
            raise ValueError("La tasa de aprendizaje debe ser positiva")

    def paso(self, pares):
        for param, grad in pares:
            param -= self.tasa * grad


class Momentum(SGD):
    nombre = "momentum"
    tasa_defecto = 0.05

    def __init__(self, tasa=None, beta=0.9):
        super().__init__(tasa)
        if not 0 <= beta < 1:
            raise ValueError("beta debe estar en [0, 1)")
        self.beta = beta
        self.velocidades = None

    def paso(self, pares):
        if self.velocidades is None:
            self.velocidades = [np.zeros_like(p) for p, _ in pares]
        for v, (param, grad) in zip(self.velocidades, pares):
            v *= self.beta
            v -= self.tasa * grad
            param += v


class Adam(SGD):
    nombre = "adam"
    tasa_defecto = 0.01

    def __init__(self, tasa=None, beta1=0.9, beta2=0.999, eps=1e-8):
        super().__init__(tasa)
        self.beta1, self.beta2, self.eps = beta1, beta2, eps
        self.m = self.v = None
        self.t = 0  # número de pasos dados (para corregir el sesgo)

    def paso(self, pares):
        if self.m is None:
            self.m = [np.zeros_like(p) for p, _ in pares]
            self.v = [np.zeros_like(p) for p, _ in pares]
        self.t += 1
        corr1 = 1 - self.beta1 ** self.t
        corr2 = 1 - self.beta2 ** self.t
        for m, v, (param, grad) in zip(self.m, self.v, pares):
            m *= self.beta1
            m += (1 - self.beta1) * grad          # media del gradiente
            v *= self.beta2
            v += (1 - self.beta2) * grad * grad   # media del gradiente al cuadrado
            m_hat, v_hat = m / corr1, v / corr2
            param -= self.tasa * m_hat / (np.sqrt(v_hat) + self.eps)


OPTIMIZADORES = {clase.nombre: clase for clase in (SGD, Momentum, Adam)}


def crear_optimizador(nombre, tasa=None):
    """Crea un optimizador por su nombre ('sgd', 'momentum', 'adam')."""
    if nombre not in OPTIMIZADORES:
        raise ValueError(
            f"Optimizador desconocido: {nombre!r}. Opciones: {', '.join(OPTIMIZADORES)}"
        )
    return OPTIMIZADORES[nombre](tasa)
