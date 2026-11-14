"""Visualización: dígitos en ASCII y gráficas en PNG."""

import numpy as np

from .datos import LADO

# De menos a más tinta
TRAMA = " .:-=+*#%@"


def digito_ascii(pixeles):
    """Dibuja una imagen (64 valores entre 0 y 1) con caracteres."""
    imagen = np.asarray(pixeles, dtype=float).reshape(LADO, LADO)
    imagen = np.clip(imagen, 0, 1)
    lineas = []
    for fila in imagen:
        # cada píxel se pinta doble para que no salga estirado en vertical
        lineas.append("".join(TRAMA[int(v * (len(TRAMA) - 1))] * 2 for v in fila))
    return "\n".join(lineas)


def barra(valor, ancho=20):
    """Barra de progreso de texto para un valor entre 0 y 1."""
    llenos = int(round(valor * ancho))
    return "█" * llenos + "░" * (ancho - llenos)


def grafica_exactitud_por_k(valores_k, exactitudes, ruta):
    """Guarda en PNG la exactitud en test para cada valor de k."""
    import matplotlib

    matplotlib.use("Agg")  # sin ventana: solo guardar a fichero
    import matplotlib.pyplot as plt

    mejor = int(np.argmax(exactitudes))
    fig, ax = plt.subplots(figsize=(6, 3.5), dpi=100)
    ax.plot(valores_k, [e * 100 for e in exactitudes], marker="o", color="#2563eb")
    ax.scatter(
        [valores_k[mejor]], [exactitudes[mejor] * 100],
        color="#dc2626", zorder=3, label=f"mejor: k={valores_k[mejor]}",
    )
    ax.set_xlabel("k (número de vecinos)")
    ax.set_ylabel("Exactitud en test (%)")
    ax.set_title("k-NN: exactitud según k")
    ax.set_xticks(valores_k)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)
    return ruta
