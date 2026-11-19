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
