"""Gráficas en PNG con matplotlib (backend sin ventana)."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

COLORES = ("#2563eb", "#ea580c")


def grafica_frontera(modelo, X, y, titulo, ruta, resolucion=200):
    """Dibuja la frontera de decisión del modelo sobre los puntos (X, y)."""
    margen = 0.5
    x0 = np.linspace(X[:, 0].min() - margen, X[:, 0].max() + margen, resolucion)
    x1 = np.linspace(X[:, 1].min() - margen, X[:, 1].max() + margen, resolucion)
    rejilla_x, rejilla_y = np.meshgrid(x0, x1)
    puntos = np.column_stack([rejilla_x.ravel(), rejilla_y.ravel()])
    zona = modelo.predecir(puntos).reshape(rejilla_x.shape)

    fig, ax = plt.subplots(figsize=(5, 4.5), dpi=80)
    ax.contourf(rejilla_x, rejilla_y, zona, levels=[-0.5, 0.5, 1.5],
                colors=["#dbeafe", "#ffedd5"])
    ax.contour(rejilla_x, rejilla_y, zona, levels=[0.5], colors="#334155", linewidths=1)
    for clase in (0, 1):
        sel = y == clase
        ax.scatter(X[sel, 0], X[sel, 1], s=14, c=COLORES[clase],
                   edgecolors="white", linewidths=0.4, label=f"clase {clase}")
    ax.set_title(titulo, fontsize=10)
    ax.legend(loc="upper right", fontsize=8)
    ax.set_xticks([])
    ax.set_yticks([])
    return _guardar(fig, ruta)


def grafica_historial(valores, etiqueta_y, titulo, ruta):
    """Curva de aprendizaje: pérdida o errores por época."""
    fig, ax = plt.subplots(figsize=(5, 3.2), dpi=80)
    ax.plot(range(1, len(valores) + 1), valores, color=COLORES[0], linewidth=1.6)
    ax.set_xlabel("época")
    ax.set_ylabel(etiqueta_y)
    ax.set_title(titulo, fontsize=10)
    ax.grid(alpha=0.3)
    return _guardar(fig, ruta)


def _guardar(fig, ruta):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)
    return ruta


def frontera_ascii(modelo, ancho=48, alto=18, limite=2.5):
    """Frontera de decisión en texto para verla directamente en la terminal."""
    xs = np.linspace(-limite, limite, ancho)
    ys = np.linspace(limite, -limite, alto)  # de arriba abajo
    lineas = []
    for yv in ys:
        puntos = np.column_stack([xs, np.full(ancho, yv)])
        pred = modelo.predecir(puntos)
        lineas.append("".join("#" if p else "." for p in pred))
    return "\n".join(lineas)


PALETA = ("#2563eb", "#ea580c", "#16a34a", "#9333ea")


def grafica_curvas(curvas, etiqueta_y, titulo, ruta, marca=None, log=False):
    """Varias curvas en una gráfica. `curvas` = {nombre: valores por época}.
    `marca` = época a señalar con una línea vertical (p. ej. la mejor)."""
    fig, ax = plt.subplots(figsize=(5.5, 3.4), dpi=80)
    for color, (nombre, valores) in zip(PALETA, curvas.items()):
        ax.plot(range(1, len(valores) + 1), valores, color=color,
                linewidth=1.6, label=nombre)
    if marca is not None:
        ax.axvline(marca, color="#64748b", linestyle="--", linewidth=1,
                   label=f"mejor época ({marca})")
    if log:
        ax.set_yscale("log")
    ax.set_xlabel("época")
    ax.set_ylabel(etiqueta_y)
    ax.set_title(titulo, fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    return _guardar(fig, ruta)


def grafica_errores_digitos(imagenes, reales, predichos, ruta, maximo=10):
    """Muestra algunos dígitos mal clasificados (imágenes 8×8)."""
    n = min(maximo, len(imagenes))
    fig, ejes = plt.subplots(1, max(n, 1), figsize=(1.1 * max(n, 1), 1.5), dpi=80)
    ejes = np.atleast_1d(ejes)
    for ax in ejes:
        ax.axis("off")
    for ax, img, r, p in zip(ejes, imagenes[:n], reales[:n], predichos[:n]):
        ax.imshow(np.asarray(img).reshape(8, 8), cmap="gray_r")
        ax.set_title(f"{r}→{p}", fontsize=9, color="#b91c1c")
    return _guardar(fig, ruta)


def grafica_pesos_digitos(W, ruta, columnas=8):
    """Pesos de la primera capa de un MLP de dígitos: cada columna de W (64
    valores) se pinta como una imagen 8×8. Rojo = peso positivo (ese píxel
    "enciende" la neurona), azul = negativo (la apaga). Cada neurona oculta
    aprende a fijarse en un trazo o zona concreta."""
    n = W.shape[1]
    filas = int(np.ceil(n / columnas))
    fig, ejes = plt.subplots(filas, columnas, figsize=(columnas * 0.9, filas * 0.95),
                             dpi=80)
    ejes = np.atleast_1d(ejes).ravel()
    for i, ax in enumerate(ejes):
        ax.axis("off")
        if i < n:
            peso = W[:, i].reshape(8, 8)
            limite = np.abs(peso).max() or 1.0
            ax.imshow(peso, cmap="RdBu_r", vmin=-limite, vmax=limite)
            ax.set_title(str(i), fontsize=7)
    fig.suptitle("Pesos de entrada de cada neurona oculta", fontsize=10)
    return _guardar(fig, ruta)
