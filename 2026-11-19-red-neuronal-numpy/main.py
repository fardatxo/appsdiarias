#!/usr/bin/env python3
"""CLI de red-neuronal-numpy.

Uso:
    python main.py datos
    python main.py entrenar [--modelo perceptron|logistica] [--dataset blobs]
                            [--tasa 0.1] [--epocas 300] [--ruido 0.2] [--graficas]
    python main.py entrenar --modelo mlp [--ocultas 16,16] [--activacion tanh]
                            [--lote 32] [--l2 0.0]
    python main.py comparar [--ruido 0.2]
    python main.py capacidad [--dataset circulos]
    python main.py gradientes [--activacion tanh]
"""

import argparse
import sys
from pathlib import Path

from red.datos import DATASETS, generar, preparar
from red.lineales import Perceptron, RegresionLogistica
from red.mlp import ACTIVACIONES, MLP, comprobar_gradientes
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
    "mlp": {"tasa": 0.1, "epocas": 500},
}


def leer_ocultas(texto):
    """'16,8' -> (16, 8). Cadena vacía o '0' -> () (sin capas ocultas)."""
    texto = texto.strip()
    if texto in ("", "0"):
        return ()
    try:
        ocultas = tuple(int(parte) for parte in texto.split(","))
    except ValueError:
        raise ValueError(f"--ocultas debe ser una lista de enteros, p. ej. 16,8 (no {texto!r})")
    if any(n <= 0 for n in ocultas):
        raise ValueError("Cada capa oculta debe tener al menos 1 neurona")
    return ocultas


def crear_modelo(nombre, tasa=None, epocas=None, **extra):
    """Fábrica de modelos a partir de su nombre en la CLI.

    `extra` son opciones solo del MLP (ocultas, activacion, tam_lote, l2)."""
    if nombre not in DEFECTOS:
        raise ValueError(f"Modelo desconocido: {nombre!r}")
    opciones = dict(DEFECTOS[nombre])
    if tasa is not None:
        opciones["tasa"] = tasa
    if epocas is not None:
        opciones["epocas"] = epocas
    if opciones["tasa"] <= 0 or opciones["epocas"] <= 0:
        raise ValueError("--tasa y --epocas deben ser positivos")
    if nombre == "mlp":
        return MLP(**opciones, **{k: v for k, v in extra.items() if v is not None})
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
    extra = {}
    if args.modelo == "mlp":
        extra = {"ocultas": leer_ocultas(args.ocultas), "activacion": args.activacion,
                 "tam_lote": args.lote, "l2": args.l2}
    modelo = crear_modelo(args.modelo, args.tasa, args.epocas, **extra).entrenar(
        X_train, y_train)
    pred_train = modelo.predecir(X_train)
    pred_test = modelo.predecir(X_test)

    print(f"Modelo: {args.modelo}  |  dataset: {args.dataset}  "
          f"(train {len(X_train)}, test {len(X_test)})")
    if isinstance(modelo, MLP):
        arquitectura = " -> ".join(str(n) for n in (2, *modelo.ocultas, 1))
        print(f"Arquitectura: {arquitectura} ({modelo.activacion}), "
              f"{modelo.num_parametros()} parámetros")
    print(f"Épocas realizadas: {len(modelo.historial)}")
    if isinstance(modelo, (RegresionLogistica, MLP)):
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
    """Tabla: exactitud en test de cada modelo en cada dataset."""
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
          "\nse queda corta. El MLP (2 capas ocultas de 16, tanh) puede curvar"
          "\nla frontera gracias a sus capas ocultas no lineales.")


def cmd_capacidad(args):
    """Exactitud según el número de neuronas de una única capa oculta."""
    X_train, X_test, y_train, y_test = preparar(args.dataset, ruido=args.ruido)
    print(f"Dataset '{args.dataset}': MLP 2 -> n -> 1 ({args.activacion}), 500 épocas\n")
    print(f"{'ocultas':>8} {'parámetros':>11} {'train':>9} {'test':>9}")
    for n in (0, 1, 2, 3, 4, 8, 16, 32):
        ocultas = (n,) if n else ()
        modelo = MLP(ocultas=ocultas, activacion=args.activacion).entrenar(X_train, y_train)
        print(f"{n:>8} {modelo.num_parametros():>11} "
              f"{exactitud(y_train, modelo.predecir(X_train)):>9.2%} "
              f"{exactitud(y_test, modelo.predecir(X_test)):>9.2%}")
    print("\n0 neuronas ocultas = regresión logística (una recta). Con pocas neuronas"
          "\nla frontera solo puede doblarse un poco; con más, se adapta a los datos.")


def cmd_gradientes(args):
    """Comprueba backpropagation contra el gradiente numérico."""
    X_train, _, y_train, _ = preparar("lunas")
    print("Comparando backprop con diferencias finitas (lunas, 20 ejemplos):\n")
    todo_bien = True
    for ocultas in ((), (4,), (5, 3), (4, 4, 4)):
        modelo = MLP(ocultas=ocultas, activacion=args.activacion, l2=0.01)
        error = comprobar_gradientes(modelo, X_train[:20], y_train[:20])
        ok = error < 1e-6
        todo_bien &= ok
        arquitectura = " -> ".join(str(n) for n in (2, *ocultas, 1))
        print(f"  {arquitectura:<22} error relativo máx. {error:.2e}  "
              f"{'OK' if ok else 'REVISAR'}")
    print("\nBackprop correcto." if todo_bien else "\nAlgo falla en backprop.")
    return 0 if todo_bien else 1


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
    p.add_argument("--ocultas", default="16,16",
                   help="neuronas por capa oculta del MLP, p. ej. 16,8 (0 = ninguna)")
    p.add_argument("--activacion", choices=list(ACTIVACIONES), default="tanh",
                   help="activación de las capas ocultas del MLP")
    p.add_argument("--lote", type=int, default=32, help="tamaño del mini-lote (MLP)")
    p.add_argument("--l2", type=float, default=0.0, help="regularización L2 (MLP)")
    p.add_argument("--graficas", action="store_true",
                   help="guarda la frontera y la curva de aprendizaje en PNG")
    p.set_defaults(func=cmd_entrenar)

    p = sub.add_parser("comparar", help="todos los modelos en todos los datasets")
    p.add_argument("--ruido", type=float, default=0.2)
    p.set_defaults(func=cmd_comparar)

    p = sub.add_parser("capacidad", help="exactitud según neuronas ocultas")
    p.add_argument("--dataset", choices=list(DATASETS), default="circulos")
    p.add_argument("--activacion", choices=list(ACTIVACIONES), default="tanh")
    p.add_argument("--ruido", type=float, default=0.2)
    p.set_defaults(func=cmd_capacidad)

    p = sub.add_parser("gradientes", help="comprueba backprop numéricamente")
    p.add_argument("--activacion", choices=list(ACTIVACIONES), default="tanh")
    p.set_defaults(func=cmd_gradientes)
    return parser


def main(argv=None):
    args = construir_parser().parse_args(argv)
    try:
        codigo = args.func(args)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return codigo or 0


if __name__ == "__main__":
    sys.exit(main())
