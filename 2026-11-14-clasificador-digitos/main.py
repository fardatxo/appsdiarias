#!/usr/bin/env python3
"""CLI del clasificador de dígitos.

Uso:
    python main.py evaluar  [--k 3] [--ponderado]
    python main.py buscar-k [--max-k 15] [--pliegues 5] [--ponderado]
    python main.py informe  [--k 3] [--ponderado]
    python main.py comparar [--k 3]
    python main.py ver      [--indice 0] [--k 3] [--guardar fichero.txt]
    python main.py dibujar  fichero.txt [--k 3] [--ponderado]
"""

import argparse
import sys
from pathlib import Path

from digitos.comparar import comparar_modelos
from digitos.datos import preparar_datos
from digitos.dibujo import leer_dibujo, pixeles_a_texto
from digitos.knn import ClasificadorKNN
from digitos.metricas import (
    exactitud,
    formatear_informe,
    formatear_matriz,
    informe_por_clase,
    matriz_confusion,
)
from digitos.validacion import elegir_k
from digitos.visual import (
    barra,
    digito_ascii,
    grafica_comparacion,
    grafica_errores,
    grafica_exactitud_por_k,
    grafica_matriz_confusion,
)

RAIZ = Path(__file__).parent
CARPETA_GRAFICAS = RAIZ / "graficas"


def _guardada(ruta):
    """Mensaje estándar tras guardar una gráfica."""
    print(f"Gráfica guardada en {Path(ruta).relative_to(RAIZ)}")


def _nombre_modelo(args):
    return f"k-NN {'ponderado ' if args.ponderado else ''}con k={args.k}"


def _entrenar(args, X_train, y_train):
    return ClasificadorKNN(k=args.k, ponderado=args.ponderado).entrenar(X_train, y_train)


def cmd_evaluar(args):
    """Entrena el k-NN y muestra exactitud y matriz de confusión en test."""
    X_train, X_test, y_train, y_test = preparar_datos()
    modelo = _entrenar(args, X_train, y_train)
    predicciones = modelo.predecir(X_test)

    print(f"Ejemplos de entrenamiento: {len(X_train)}  |  de test: {len(X_test)}")
    print(_nombre_modelo(args))
    aciertos = int((predicciones == y_test).sum())
    print(f"Exactitud en test: {exactitud(y_test, predicciones):.2%} "
          f"({aciertos}/{len(y_test)} aciertos)\n")
    print("Matriz de confusión (fila = dígito real, columna = predicho):")
    print(formatear_matriz(matriz_confusion(y_test, predicciones, modelo.clases),
                           modelo.clases))


def cmd_buscar_k(args):
    """Elige k con validación cruzada (sin mirar el test) y guarda una gráfica."""
    X_train, X_test, y_train, y_test = preparar_datos()
    valores_k = list(range(1, args.max_k + 1, 2))  # impares: menos empates
    if not valores_k:
        raise ValueError("--max-k debe ser al menos 1")

    mejor_k, validacion = elegir_k(
        X_train, y_train, valores_k, args.pliegues, args.ponderado
    )
    en_test = []
    # la barra va de 90 % a 100 % para que se aprecien las diferencias
    print(f"{'k':>4}  {'validación cruzada (barra: 90-100 %)':<28}  test")
    for k, media in zip(valores_k, validacion):
        modelo = ClasificadorKNN(k=k, ponderado=args.ponderado).entrenar(X_train, y_train)
        en_test.append(exactitud(y_test, modelo.predecir(X_test)))
        print(f"{k:>4}  {barra(max(0.0, (media - 0.9) / 0.1))} {media:.2%}"
              f"{'':>10}{en_test[-1]:.2%}")

    posicion = valores_k.index(mejor_k)
    print(f"\nk elegido por validación cruzada ({args.pliegues} pliegues): {mejor_k} "
          f"({validacion[posicion]:.2%} en validación, {en_test[posicion]:.2%} en test)")
    CARPETA_GRAFICAS.mkdir(exist_ok=True)
    _guardada(grafica_exactitud_por_k(
        valores_k, en_test, CARPETA_GRAFICAS / "exactitud_por_k.png", validacion
    ))


def cmd_informe(args):
    """Precisión/recall/F1 por clase, matriz de confusión en PNG y galería de errores."""
    X_train, X_test, y_train, y_test = preparar_datos()
    modelo = _entrenar(args, X_train, y_train)
    predicciones = modelo.predecir(X_test)
    matriz = matriz_confusion(y_test, predicciones, modelo.clases)

    print(f"{_nombre_modelo(args)} — exactitud en test: "
          f"{exactitud(y_test, predicciones):.2%}\n")
    print(formatear_informe(informe_por_clase(matriz), modelo.clases))

    fallos = predicciones != y_test
    print(f"\nErrores: {int(fallos.sum())} de {len(y_test)}")
    for indice in fallos.nonzero()[0]:
        print(f"  test[{indice}]: era un {y_test[indice]} y dice {predicciones[indice]}")

    print()
    CARPETA_GRAFICAS.mkdir(exist_ok=True)
    _guardada(grafica_matriz_confusion(
        matriz, modelo.clases, CARPETA_GRAFICAS / "matriz_confusion.png",
        f"Matriz de confusión ({_nombre_modelo(args)})",
    ))
    if fallos.any():
        _guardada(grafica_errores(
            X_test[fallos], y_test[fallos], predicciones[fallos],
            CARPETA_GRAFICAS / "errores.png",
        ))


def cmd_comparar(args):
    """Compara el k-NN propio con modelos de scikit-learn sobre los mismos datos."""
    X_train, X_test, y_train, y_test = preparar_datos()
    resultados = comparar_modelos(X_train, y_train, X_test, y_test, args.k)

    ancho = max(len(r["nombre"]) for r in resultados)
    print(f"{'modelo':<{ancho}}  exactitud  F1 macro  fallos  entrenar  predecir")
    for r in resultados:
        print(f"{r['nombre']:<{ancho}}  {r['exactitud']:>9.2%}  {r['f1']:>8.2%}  "
              f"{r['fallos']:>6}  {r['t_entrenar'] * 1000:>6.0f} ms  "
              f"{r['t_predecir'] * 1000:>5.0f} ms")
    print()
    CARPETA_GRAFICAS.mkdir(exist_ok=True)
    _guardada(grafica_comparacion(resultados, CARPETA_GRAFICAS / "comparacion_modelos.png"))


def _explicar_prediccion(modelo, imagen, y_train):
    """Imprime los votos y los vecinos que justifican la predicción."""
    probabilidades = modelo.predecir_proba(imagen)[0]
    indices, distancias = modelo.vecinos(imagen)
    print(f"Votos de los {modelo.k} vecinos más cercanos:")
    for clase, p in zip(modelo.clases, probabilidades):
        if p > 0:
            print(f"  {clase}: {barra(p, 10)} {p:.0%}")
    vecinos = ", ".join(
        f"{y_train[i]} (dist. {d:.2f})" for i, d in zip(indices[0], distancias[0])
    )
    print(f"Vecinos: {vecinos}")


def cmd_ver(args):
    """Dibuja un dígito del conjunto de test y enseña cómo lo clasifica el modelo."""
    X_train, X_test, y_train, y_test = preparar_datos()
    if not 0 <= args.indice < len(X_test):
        sys.exit(f"Error: el índice debe estar entre 0 y {len(X_test) - 1}")

    modelo = _entrenar(args, X_train, y_train)
    imagen = X_test[args.indice]
    prediccion = modelo.predecir(imagen)[0]

    print(digito_ascii(imagen))
    real = y_test[args.indice]
    marca = "✔ acierto" if prediccion == real else "✘ fallo"
    print(f"\nDígito real: {real}  |  Predicción: {prediccion}  ({marca})\n")
    _explicar_prediccion(modelo, imagen, y_train)

    if args.guardar:
        # se guarda en el formato que entiende `dibujar`, para poder retocarlo
        Path(args.guardar).write_text(pixeles_a_texto(imagen), encoding="utf-8")
        print(f"\nDígito guardado en {args.guardar} (prueba a editarlo y usar `dibujar`)")


def cmd_dibujar(args):
    """Clasifica un dígito de 8x8 dibujado en un fichero de texto."""
    imagen = leer_dibujo(args.fichero)
    X_train, _, y_train, _ = preparar_datos()
    modelo = _entrenar(args, X_train, y_train)

    print(digito_ascii(imagen))
    print(f"\nEl modelo cree que es un: {modelo.predecir(imagen)[0]}\n")
    _explicar_prediccion(modelo, imagen, y_train)


def _k_positivo(texto):
    """Tipo de argparse: entero mayor o igual que 1."""
    try:
        valor = int(texto)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{texto!r} no es un número entero")
    if valor < 1:
        raise argparse.ArgumentTypeError("debe ser mayor o igual que 1")
    return valor


def crear_parser():
    parser = argparse.ArgumentParser(
        description="Clasificador de dígitos manuscritos con k-NN hecho a mano."
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    def opciones_knn(p, ponderado=True):
        p.add_argument("--k", type=_k_positivo, default=3,
                       help="número de vecinos (por defecto 3)")
        if ponderado:
            p.add_argument("--ponderado", action="store_true",
                           help="los vecinos más cercanos votan con más peso")

    p = sub.add_parser("evaluar", help="exactitud y matriz de confusión en test")
    opciones_knn(p)
    p.set_defaults(func=cmd_evaluar)

    p = sub.add_parser("buscar-k", help="elige k con validación cruzada y guarda una gráfica")
    p.add_argument("--max-k", type=_k_positivo, default=15, help="k máximo a probar")
    p.add_argument("--pliegues", type=int, default=5,
                   help="trozos de la validación cruzada (por defecto 5)")
    p.add_argument("--ponderado", action="store_true",
                   help="los vecinos más cercanos votan con más peso")
    p.set_defaults(func=cmd_buscar_k)

    p = sub.add_parser("informe", help="precisión/recall por clase y gráficas de errores")
    opciones_knn(p)
    p.set_defaults(func=cmd_informe)

    p = sub.add_parser("comparar", help="k-NN propio frente a modelos de scikit-learn")
    opciones_knn(p, ponderado=False)
    p.set_defaults(func=cmd_comparar)

    p = sub.add_parser("ver", help="dibuja un dígito de test y lo clasifica")
    p.add_argument("--indice", type=int, default=0, help="posición en el test")
    opciones_knn(p)
    p.add_argument("--guardar", metavar="FICHERO",
                   help="guarda el dígito como texto editable para `dibujar`")
    p.set_defaults(func=cmd_ver)

    p = sub.add_parser("dibujar", help="clasifica un dígito 8x8 escrito en un fichero de texto")
    p.add_argument("fichero", help="fichero con el dibujo (ver ejemplos/)")
    opciones_knn(p)
    p.set_defaults(func=cmd_dibujar)
    return parser


def main(argv=None):
    args = crear_parser().parse_args(argv)
    try:
        args.func(args)
    except (ValueError, OSError) as error:
        sys.exit(f"Error: {error}")


if __name__ == "__main__":
    main()
