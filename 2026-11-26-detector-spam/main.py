"""CLI del detector de spam.

Uso:
    python main.py generar [--n 1200] [--semilla 42]   # crea datos/mensajes.csv
    python main.py datos                               # resumen y ejemplos del dataset
    python main.py evaluar [--alfa 1.0] [--grafica]    # entrena con train y evalúa en test
    python main.py predecir "texto del mensaje" [...]  # clasifica mensajes nuevos
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

import numpy as np

from spam.bayes import NaiveBayesMultinomial
from spam.datos import ETIQUETAS, RUTA_CSV, cargar_csv, dividir_train_test, generar_mensajes, guardar_csv
from spam.metricas import formatear_informe, informe
from spam.texto import tokenizar
from spam.vectorizador import BolsaDePalabras

CARPETA_GRAFICAS = Path(__file__).resolve().parent / "graficas"


def entrenar_modelo(textos_train, y_train, alfa=1.0, min_frecuencia=1):
    """Ajusta vocabulario y Naive Bayes. Devuelve (vectorizador, modelo)."""
    vec = BolsaDePalabras(min_frecuencia=min_frecuencia)
    X = vec.ajustar_transformar(textos_train)
    modelo = NaiveBayesMultinomial(alfa=alfa).entrenar(X, y_train)
    return vec, modelo


def preparar(args):
    textos, y = cargar_csv(Path(args.csv))
    return dividir_train_test(textos, y, prop_test=args.test, semilla=args.semilla)


# --- Subcomandos -----------------------------------------------------------

def cmd_generar(args):
    mensajes = generar_mensajes(n=args.n, prop_spam=args.prop_spam, semilla=args.semilla)
    guardar_csv(mensajes, Path(args.csv))
    n_spam = sum(e == "spam" for _, e in mensajes)
    print(f"Generados {len(mensajes)} mensajes ({n_spam} spam, {len(mensajes) - n_spam} ham)"
          f" en {args.csv}")


def cmd_datos(args):
    textos, y = cargar_csv(Path(args.csv))
    print(f"Mensajes: {len(textos)}  ·  spam: {int(y.sum())} ({y.mean():.1%})"
          f"  ·  ham: {int((y == 0).sum())}")
    longitudes = np.array([len(t) for t in textos])
    for k, nombre in enumerate(ETIQUETAS):
        print(f"Longitud media {nombre:4s}: {longitudes[y == k].mean():.0f} caracteres")
    for k, nombre in enumerate(ETIQUETAS):
        cuentas = Counter(tok for t, yy in zip(textos, y) if yy == k for tok in tokenizar(t))
        top = ", ".join(f"{p} ({c})" for p, c in cuentas.most_common(10))
        print(f"\nTokens más frecuentes en {nombre}: {top}")
    rng = np.random.default_rng(args.semilla)
    print("\nEjemplos:")
    for i in rng.choice(len(textos), size=min(6, len(textos)), replace=False):
        print(f"  [{ETIQUETAS[y[i]]:4s}] {textos[i]}")


def cmd_evaluar(args):
    tx_train, tx_test, y_train, y_test = preparar(args)
    vec, modelo = entrenar_modelo(tx_train, y_train, alfa=args.alfa,
                                  min_frecuencia=args.min_frecuencia)
    print(f"Train: {len(tx_train)} mensajes · Test: {len(tx_test)} mensajes · "
          f"Vocabulario: {len(vec.vocabulario)} palabras · alfa = {args.alfa}")

    for nombre, textos, y in (("train", tx_train, y_train), ("test", tx_test, y_test)):
        pred = modelo.predecir(vec.transformar(textos))
        print(f"\nResultados en {nombre}:")
        print(formatear_informe(informe(y, pred)))

    palabras_spam, palabras_ham = modelo.palabras_mas_indicativas(vec.palabras, n=10)
    print("\nPalabras que más delatan al spam (log P(w|spam) - log P(w|ham)):")
    print("  " + ", ".join(f"{p} ({r:+.1f})" for p, r in palabras_spam))
    print("Palabras más típicas de ham:")
    print("  " + ", ".join(f"{p} ({r:+.1f})" for p, r in palabras_ham))

    # Errores en test: ayudan a entender dónde falla el modelo.
    X_test = vec.transformar(tx_test)
    pred = modelo.predecir(X_test)
    proba = modelo.predecir_proba(X_test)[:, 1]
    errores = np.flatnonzero(pred != y_test)
    if len(errores):
        print(f"\nAlgunos errores en test ({len(errores)} en total):")
        for i in errores[:8]:
            print(f"  real={ETIQUETAS[y_test[i]]:4s} P(spam)={proba[i]:.2f}  {tx_test[i]}")

    if args.grafica:
        ruta = guardar_grafica_palabras(palabras_spam, palabras_ham)
        print(f"\nGráfica guardada en {ruta}")


def cmd_predecir(args):
    textos, y = cargar_csv(Path(args.csv))
    vec, modelo = entrenar_modelo(textos, y, alfa=args.alfa)  # usa todos los datos
    proba = modelo.predecir_proba(vec.transformar(args.mensajes))[:, 1]
    for texto, p in zip(args.mensajes, proba):
        etiqueta = "SPAM" if p >= 0.5 else "ham "
        print(f"[{etiqueta}] P(spam) = {p:.3f}  ·  {texto}")
        conocidas = [t for t in tokenizar(texto) if t in vec.vocabulario]
        print(f"         tokens usados: {' '.join(conocidas) or '(ninguno conocido)'}")


def guardar_grafica_palabras(palabras_spam, palabras_ham) -> Path:
    """Barras horizontales con las palabras más indicativas de cada clase."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    datos = list(reversed(palabras_spam)) + list(palabras_ham)[::-1]
    datos.sort(key=lambda pr: pr[1])
    etiquetas = [p for p, _ in datos]
    valores = [r for _, r in datos]
    colores = ["#c0392b" if v > 0 else "#2e86c1" for v in valores]
    fig, ax = plt.subplots(figsize=(6, 5), dpi=90)
    ax.barh(etiquetas, valores, color=colores)
    ax.axvline(0, color="#555", linewidth=0.8)
    ax.set_xlabel("log P(palabra | spam) − log P(palabra | ham)")
    ax.set_title("Palabras más indicativas (rojo = spam, azul = ham)")
    fig.tight_layout()
    CARPETA_GRAFICAS.mkdir(exist_ok=True)
    ruta = CARPETA_GRAFICAS / "palabras_indicativas.png"
    fig.savefig(ruta)
    plt.close(fig)
    return ruta


# --- Argumentos ------------------------------------------------------------

def crear_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Detector de spam con Naive Bayes hecho a mano")
    p.add_argument("--csv", default=str(RUTA_CSV), help="ruta del dataset CSV")
    sub = p.add_subparsers(dest="comando", required=True)

    g = sub.add_parser("generar", help="genera el dataset sintético de SMS")
    g.add_argument("--n", type=int, default=1200)
    g.add_argument("--prop-spam", type=float, default=0.35)
    g.add_argument("--semilla", type=int, default=42)
    g.set_defaults(func=cmd_generar)

    d = sub.add_parser("datos", help="resumen del dataset")
    d.add_argument("--semilla", type=int, default=0)
    d.set_defaults(func=cmd_datos)

    e = sub.add_parser("evaluar", help="entrena en train y evalúa en test")
    e.add_argument("--alfa", type=float, default=1.0, help="suavizado de Laplace")
    e.add_argument("--min-frecuencia", type=int, default=1)
    e.add_argument("--test", type=float, default=0.25, help="proporción de test")
    e.add_argument("--semilla", type=int, default=0)
    e.add_argument("--grafica", action="store_true", help="guarda un PNG con las palabras clave")
    e.set_defaults(func=cmd_evaluar)

    pr = sub.add_parser("predecir", help="clasifica mensajes nuevos")
    pr.add_argument("mensajes", nargs="+")
    pr.add_argument("--alfa", type=float, default=1.0)
    pr.set_defaults(func=cmd_predecir)
    return p


def main(argv=None) -> int:
    args = crear_parser().parse_args(argv)
    try:
        args.func(args)
    except (FileNotFoundError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
