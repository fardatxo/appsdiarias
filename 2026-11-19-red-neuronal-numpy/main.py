#!/usr/bin/env python3
"""CLI de red-neuronal-numpy.

Uso:
    python main.py datos
    python main.py entrenar [--modelo perceptron|logistica] [--dataset blobs]
                            [--tasa 0.1] [--epocas 300] [--ruido 0.2] [--graficas]
    python main.py comparar [--ruido 0.2]
"""

import argparse
import sys
from pathlib import Path

from red.datos import DATASETS, generar, preparar
from red.lineales import Perceptron, RegresionLogistica
from red.metricas import (
    entropia_cruzada_binaria,
    exactitud,
    formatear_matriz,
    matriz_confusion,
    precision_recall_f1,
)
from red.visual import frontera_ascii, grafica_frontera, grafica_historial

RAIZ = Path(__file__).parent
CARPETA_GRAFICAS = RAIZ / "graficas"

# Valores por defecto razonables para cada modelo
DEFECTOS = {
    "perceptron": {"tasa": 0.1, "epocas": 50},
    "logistica": {"tasa": 0.5, "epocas": 300},
}


def crear_modelo(nombre, tasa=None, epocas=None):
    """Fábrica de modelos a partir de su nombre en la CLI."""
    if nombre not in DEFECTOS:
        raise ValueError(f"Modelo desconocido: {nombre!r}")
    opciones = dict(DEFECTOS[nombre])
    if tasa is not None:
        opciones["tasa"] = tasa
    if epocas is not None:
        opciones["epocas"] = epocas
    if opciones["tasa"] <= 0 or opciones["epocas"] <= 0:
        raise ValueError("--tasa y --epocas deben ser positivos")
    clase = Perceptron if nombre == "perceptron" else RegresionLogistica
    return clase(**opciones)


def cmd_datos(_args):
    """Resumen de los datasets disponibles."""
    print(f"{'dataset':<10} {'n':>4} {'clase 1':>8}  {'¿lineal?':<9} descripción")
    for nombre, (descripcion, lineal) in DATASETS.items():
        X, y = generar(nombre)
        print(f"{nombre:<10} {len(X):>4} {int(y.sum()):>8}  "
              f"{'sí' if lineal else 'no':<9} {descripcion}")


def cmd_entrenar(args):
    """Entrena un modelo en un dataset y muestra su evaluación en test."""
    X_train, X_test, y_train, y_test = preparar(args.dataset, ruido=args.ruido)
    modelo = crear_modelo(args.modelo, args.tasa, args.epocas).entrenar(X_train, y_train)
    pred_train = modelo.predecir(X_train)
    pred_test = modelo.predecir(X_test)

    print(f"Modelo: {args.modelo}  |  dataset: {args.dataset}  "
          f"(train {len(X_train)}, test {len(X_test)})")
    print(f"Épocas realizadas: {len(modelo.historial)}")
    if isinstance(modelo, RegresionLogistica):
        perdida = entropia_cruzada_binaria(y_test, modelo.probabilidades(X_test))
        print(f"Pérdida (entropía cruzada) en test: {perdida:.4f}")
    print(f"Exactitud train: {exactitud(y_train, pred_train):.2%}")
    print(f"Exactitud test:  {exactitud(y_test, pred_test):.2%}")
    precision, recall, f1 = precision_recall_f1(y_test, pred_test)
    print(f"Precisión {precision:.2f} · Recall {recall:.2f} · F1 {f1:.2f}\n")
    print("Matriz de confusión (test):")
    print(formatear_matriz(matriz_confusion(y_test, pred_test)))
    print("\nFrontera de decisión ('#' = clase 1, '.' = clase 0):")
    print(frontera_ascii(modelo))

    if args.graficas:
        base = f"{args.modelo}_{args.dataset}"
        ruta = grafica_frontera(modelo, X_test, y_test,
                                f"{args.modelo} en '{args.dataset}' (test)",
                                CARPETA_GRAFICAS / f"frontera_{base}.png")
        print(f"\nGráfica guardada en {ruta.relative_to(RAIZ)}")
        etiqueta = "errores" if args.modelo == "perceptron" else "pérdida"
        ruta = grafica_historial(modelo.historial, etiqueta,
                                 f"Aprendizaje de {args.modelo} en '{args.dataset}'",
                                 CARPETA_GRAFICAS / f"historial_{base}.png")
        print(f"Gráfica guardada en {ruta.relative_to(RAIZ)}")


def cmd_comparar(args):
    """Tabla: exactitud en test de cada modelo lineal en cada dataset."""
    modelos = list(DEFECTOS)
    print(f"{'dataset':<10}" + "".join(f"{m:>12}" for m in modelos))
    for nombre in DATASETS:
        X_train, X_test, y_train, y_test = preparar(nombre, ruido=args.ruido)
        fila = f"{nombre:<10}"
        for m in modelos:
            modelo = crear_modelo(m).entrenar(X_train, y_train)
            fila += f"{exactitud(y_test, modelo.predecir(X_test)):>12.2%}"
        print(fila)
    print("\nUna sola neurona solo traza rectas: en 'lunas', 'circulos' y 'xor'"
          "\nse queda corta. Para eso hará falta la red multicapa (MLP).")


def construir_parser():
    parser = argparse.ArgumentParser(
        description="Redes neuronales desde cero con numpy")
    sub = parser.add_subparsers(dest="comando", required=True)

    sub.add_parser("datos", help="lista los datasets disponibles").set_defaults(
        func=cmd_datos)

    p = sub.add_parser("entrenar", help="entrena y evalúa un modelo")
    p.add_argument("--modelo", choices=list(DEFECTOS), default="logistica")
    p.add_argument("--dataset", choices=list(DATASETS), default="blobs")
    p.add_argument("--tasa", type=float, help="tasa de aprendizaje")
    p.add_argument("--epocas", type=int, help="número máximo de épocas")
    p.add_argument("--ruido", type=float, default=0.2)
    p.add_argument("--graficas", action="store_true",
                   help="guarda la frontera y la curva de aprendizaje en PNG")
    p.set_defaults(func=cmd_entrenar)

    p = sub.add_parser("comparar", help="modelos lineales en todos los datasets")
    p.add_argument("--ruido", type=float, default=0.2)
    p.set_defaults(func=cmd_comparar)
    return parser


def main(argv=None):
    args = construir_parser().parse_args(argv)
    try:
        args.func(args)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
