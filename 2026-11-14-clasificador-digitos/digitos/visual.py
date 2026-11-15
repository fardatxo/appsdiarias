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


def _pyplot():
    """Importa matplotlib sin ventana (solo para guardar ficheros)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def grafica_exactitud_por_k(valores_k, exactitudes, ruta, validacion=None):
    """Guarda en PNG la exactitud en test para cada valor de k.

    Si se pasa `validacion` (exactitud media de validación cruzada para cada k)
    se dibuja también, y el k marcado es el que elige la validación.
    """
    plt = _pyplot()
    fig, ax = plt.subplots(figsize=(6, 3.5), dpi=100)
    ax.plot(valores_k, [e * 100 for e in exactitudes], marker="o",
            color="#2563eb", label="test")
    elegidas = exactitudes if validacion is None else validacion
    if validacion is not None:
        ax.plot(valores_k, [e * 100 for e in validacion], marker="s",
                color="#16a34a", linestyle="--", label="validación cruzada")
    mejor = int(np.argmax(elegidas))
    ax.scatter(
        [valores_k[mejor]], [elegidas[mejor] * 100],
        color="#dc2626", zorder=3, label=f"elegido: k={valores_k[mejor]}",
    )
    ax.set_xlabel("k (número de vecinos)")
    ax.set_ylabel("Exactitud (%)")
    ax.set_title("k-NN: exactitud según k")
    ax.set_xticks(valores_k)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)
    return ruta


def grafica_matriz_confusion(matriz, clases, ruta, titulo="Matriz de confusión"):
    """Guarda la matriz de confusión como mapa de calor."""
    plt = _pyplot()
    matriz = np.asarray(matriz)
    fig, ax = plt.subplots(figsize=(5, 4.5), dpi=100)
    ax.imshow(matriz, cmap="Blues")
    ax.set_xticks(range(len(clases)), clases)
    ax.set_yticks(range(len(clases)), clases)
    ax.set_xlabel("Dígito predicho")
    ax.set_ylabel("Dígito real")
    ax.set_title(titulo)
    umbral = matriz.max() / 2
    for f in range(matriz.shape[0]):
        for c in range(matriz.shape[1]):
            if matriz[f, c]:
                # los errores (fuera de la diagonal) se resaltan en rojo
                color = "white" if matriz[f, c] > umbral else ("#dc2626" if f != c else "black")
                ax.text(c, f, matriz[f, c], ha="center", va="center", color=color, fontsize=9)
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)
    return ruta


def grafica_errores(imagenes, reales, predichos, ruta, maximo=12):
    """Galería con las imágenes que el modelo ha clasificado mal."""
    plt = _pyplot()
    n = min(len(imagenes), maximo)
    if n == 0:
        raise ValueError("No hay errores que dibujar")
    columnas = min(n, 4)
    filas = int(np.ceil(n / columnas))
    fig, ejes = plt.subplots(filas, columnas, figsize=(1.6 * columnas, 1.9 * filas), dpi=100)
    ejes = np.atleast_1d(ejes).ravel()
    for eje in ejes:
        eje.axis("off")
    for eje, imagen, real, pred in zip(ejes, imagenes[:n], reales[:n], predichos[:n]):
        eje.imshow(np.asarray(imagen).reshape(LADO, LADO), cmap="gray_r", vmin=0, vmax=1)
        eje.set_title(f"real {real} → dice {pred}", fontsize=8, color="#dc2626")
    fig.suptitle("Errores del modelo", fontsize=10)
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)
    return ruta


def grafica_comparacion(resultados, ruta):
    """Barras horizontales con la exactitud en test de cada modelo."""
    plt = _pyplot()
    orden = list(reversed(resultados))  # el mejor queda arriba
    nombres = [r["nombre"] for r in orden]
    valores = [r["exactitud"] * 100 for r in orden]
    colores = ["#2563eb" if "propio" in n else "#94a3b8" for n in nombres]
    fig, ax = plt.subplots(figsize=(6.5, 3), dpi=100)
    barras = ax.barh(nombres, valores, color=colores)
    ax.bar_label(barras, fmt="%.2f %%", padding=3, fontsize=8)
    ax.set_xlim(min(valores) - 2, 100.9)
    ax.set_xlabel("Exactitud en test (%)")
    ax.set_title("k-NN propio (azul) frente a scikit-learn")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)
    return ruta
