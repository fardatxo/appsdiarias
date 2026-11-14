#!/usr/bin/env python3
"""CLI del clasificador de dígitos.

Uso:
    python main.py evaluar [--k 3]
    python main.py buscar-k [--max-k 15]
    python main.py ver [--indice 0] [--k 3]
"""

import argparse
import sys
from pathlib import Path

from digitos.datos import preparar_datos
from digitos.knn import ClasificadorKNN
from digitos.metricas import exactitud, formatear_matriz, matriz_confusion
from digitos.visual import barra, digito_ascii, grafica_exactitud_por_k

CARPETA_GRAFICAS = Path(__file__).parent / "graficas"


def cmd_evaluar(args):
    """Entrena el k-NN y muestra exactitud y matriz de confusión en test."""
    X_train, X_test, y_train, y_test = preparar_datos()
    modelo = ClasificadorKNN(k=args.k).entrenar(X_train, y_train)
    predicciones = modelo.predecir(X_test)

    print(f"Ejemplos de entrenamiento: {len(X_train)}  |  de test: {len(X_test)}")
    print(f"k-NN con k={args.k}")
    aciertos = int((predicciones == y_test).sum())
    print(f"Exactitud en test: {exactitud(y_test, predicciones):.2%} "
          f"({aciertos}/{len(y_test)} aciertos)\n")
    print("Matriz de confusión (fila = dígito real, columna = predicho):")
    print(formatear_matriz(matriz_confusion(y_test, predicciones, modelo.clases),
                           modelo.clases))


def cmd_buscar_k(args):
    """Prueba varios valores de k y guarda una gráfica con el resultado."""
    X_train, X_test, y_train, y_test = preparar_datos()
    valores_k = list(range(1, args.max_k + 1, 2))  # impares: menos empates
    exactitudes = []
    for k in valores_k:
        modelo = ClasificadorKNN(k=k).entrenar(X_train, y_train)
        valor = exactitud(y_test, modelo.predecir(X_test))
        exactitudes.append(valor)
        print(f"k={k:>2}  {barra(valor)}  {valor:.2%}")

    mejor = max(range(len(valores_k)), key=lambda i: exactitudes[i])
    print(f"\nMejor k: {valores_k[mejor]} ({exactitudes[mejor]:.2%})")
    CARPETA_GRAFICAS.mkdir(exist_ok=True)
    ruta = grafica_exactitud_por_k(
        valores_k, exactitudes, CARPETA_GRAFICAS / "exactitud_por_k.png"
    )
    print(f"Gráfica guardada en {ruta.relative_to(Path(__file__).parent)}")


def cmd_ver(args):
    """Dibuja un dígito del conjunto de test y enseña cómo lo clasifica el modelo."""
    X_train, X_test, y_train, y_test = preparar_datos()
    if not 0 <= args.indice < len(X_test):
        sys.exit(f"Error: el índice debe estar entre 0 y {len(X_test) - 1}")

    modelo = ClasificadorKNN(k=args.k).entrenar(X_train, y_train)
    imagen = X_test[args.indice]
    prediccion = modelo.predecir(imagen)[0]
    probabilidades = modelo.predecir_proba(imagen)[0]
    indices, distancias = modelo.vecinos(imagen)

    print(digito_ascii(imagen))
    real = y_test[args.indice]
    marca = "✔ acierto" if prediccion == real else "✘ fallo"
    print(f"\nDígito real: {real}  |  Predicción: {prediccion}  ({marca})\n")
    print(f"Votos de los {args.k} vecinos más cercanos:")
    for clase, p in zip(modelo.clases, probabilidades):
        if p > 0:
            print(f"  {clase}: {barra(p, 10)} {p:.0%}")
    vecinos = ", ".join(
        f"{y_train[i]} (dist. {d:.2f})" for i, d in zip(indices[0], distancias[0])
    )
    print(f"Vecinos: {vecinos}")


def crear_parser():
    parser = argparse.ArgumentParser(
        description="Clasificador de dígitos manuscritos con k-NN hecho a mano."
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("evaluar", help="exactitud y matriz de confusión en test")
    p.add_argument("--k", type=int, default=3, help="número de vecinos (por defecto 3)")
    p.set_defaults(func=cmd_evaluar)

    p = sub.add_parser("buscar-k", help="compara valores de k y guarda una gráfica")
    p.add_argument("--max-k", type=int, default=15, help="k máximo a probar")
    p.set_defaults(func=cmd_buscar_k)

    p = sub.add_parser("ver", help="dibuja un dígito de test y lo clasifica")
    p.add_argument("--indice", type=int, default=0, help="posición en el test")
    p.add_argument("--k", type=int, default=3, help="número de vecinos")
    p.set_defaults(func=cmd_ver)
    return parser


def main(argv=None):
    args = crear_parser().parse_args(argv)
    try:
        args.func(args)
    except ValueError as error:
        sys.exit(f"Error: {error}")


if __name__ == "__main__":
    main()
