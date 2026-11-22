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
    python main.py optimizadores [--dataset lunas] [--epocas 100] [--graficas]
    python main.py inicializacion [--activacion tanh] [--capas 8]
    python main.py digitos [--optimizador adam] [--ocultas 32] [--paciencia 15] [--graficas]
                           [--guardar modelos/digitos.npz]
    python main.py predecir --modelo modelos/lunas.npz [--punto 0.5,-0.2 ...]
    python main.py predecir --modelo modelos/digitos.npz [--indice 3 | --dibujo ejemplos/siete.txt]
    python main.py sklearn                    # nuestro MLP frente a MLPClassifier
"""

import argparse
import sys
import time
import warnings
from pathlib import Path

import numpy as np

from red.datos import (
    DATASETS,
    dibujo_ascii,
    dividir_digitos_crudos,
    generar,
    leer_dibujo,
    preparar,
    preparar_digitos,
)
from red.lineales import Perceptron, RegresionLogistica
from red.metricas import (
    entropia_cruzada_binaria,
    entropia_cruzada_categorica,
    exactitud,
    formatear_matriz,
    formatear_matriz_multiclase,
    matriz_confusion,
    matriz_confusion_multiclase,
    precision_recall_f1,
)
from red.mlp import (
    ACTIVACIONES,
    INICIALIZACIONES,
    MLP,
    comprobar_gradientes,
    desviacion_activaciones,
)
from red.optimizadores import OPTIMIZADORES
from red.persistencia import cargar_modelo, guardar_modelo
from red.visual import (
    frontera_ascii,
    grafica_curvas,
    grafica_errores_digitos,
    grafica_frontera,
    grafica_historial,
    grafica_pesos_digitos,
)

RAIZ = Path(__file__).parent
CARPETA_GRAFICAS = RAIZ / "graficas"

# Valores por defecto razonables para cada modelo
DEFECTOS = {
    "perceptron": {"tasa": 0.1, "epocas": 50},
    "logistica": {"tasa": 0.5, "epocas": 300},
    "mlp": {"tasa": None, "epocas": 500},  # tasa None = la del optimizador
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

    `extra` son opciones solo del MLP (ocultas, activacion, tam_lote, l2,
    optimizador, inicializacion, validacion, paciencia)."""
    if nombre not in DEFECTOS:
        raise ValueError(f"Modelo desconocido: {nombre!r}")
    opciones = dict(DEFECTOS[nombre])
    if tasa is not None:
        opciones["tasa"] = tasa
    if epocas is not None:
        opciones["epocas"] = epocas
    if (opciones["tasa"] is not None and opciones["tasa"] <= 0) or opciones["epocas"] <= 0:
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
    if args.guardar and args.modelo != "mlp":
        raise ValueError("--guardar solo funciona con --modelo mlp")
    X_train, X_test, y_train, y_test, escala = preparar(args.dataset, ruido=args.ruido,
                                                        con_escala=True)
    extra = {}
    if args.modelo == "mlp":
        extra = {"ocultas": leer_ocultas(args.ocultas), "activacion": args.activacion,
                 "tam_lote": args.lote, "l2": args.l2, "optimizador": args.optimizador,
                 "inicializacion": args.init, "validacion": args.validacion,
                 "paciencia": args.paciencia}
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
        print(f"Optimizador: {modelo.optimizador} (tasa {modelo.tasa:g}), "
              f"inicialización {modelo.inicializacion}")
    print(f"Épocas realizadas: {len(modelo.historial)}")
    if isinstance(modelo, MLP) and modelo.mejor_epoca:
        print(f"Mejor época en validación: {modelo.mejor_epoca}"
              + (" (pesos restaurados)" if modelo.paciencia else ""))
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

    if args.guardar:
        ruta = guardar_modelo(modelo, args.guardar, escala, info={
            "tipo": "2d", "dataset": args.dataset, "ruido": args.ruido,
            "exactitud_test": exactitud(y_test, pred_test)})
        print(f"\nModelo guardado en {ruta}")


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


def cmd_optimizadores(args):
    """Mismo MLP y mismos datos, tres optimizadores distintos."""
    X_train, X_test, y_train, y_test = preparar(args.dataset, ruido=args.ruido)
    print(f"Dataset '{args.dataset}': MLP 2 -> 16 -> 16 -> 1 (tanh), "
          f"{args.epocas} épocas, lotes de 32\n")
    print(f"{'optimizador':<12} {'tasa':>6} {'pérdida ép.10':>14} "
          f"{'pérdida final':>14} {'test':>8}")
    curvas = {}
    for nombre in OPTIMIZADORES:
        modelo = MLP(ocultas=(16, 16), optimizador=nombre, epocas=args.epocas)
        modelo.entrenar(X_train, y_train)
        curvas[nombre] = modelo.historial
        decima = modelo.historial[min(9, len(modelo.historial) - 1)]
        print(f"{nombre:<12} {modelo.tasa:>6g} {decima:>14.4f} "
              f"{modelo.historial[-1]:>14.4f} "
              f"{exactitud(y_test, modelo.predecir(X_test)):>8.2%}")
    print("\nMomentum y Adam bajan la pérdida de train mucho antes que SGD: aprovechan"
          "\nla inercia (y Adam, además, adapta el paso de cada peso). Ojo: menos"
          "\npérdida en train no garantiza más exactitud en test (sobreajuste).")
    if args.graficas:
        ruta = grafica_curvas(curvas, "pérdida en train (escala log)",
                              f"Optimizadores en '{args.dataset}'",
                              CARPETA_GRAFICAS / f"optimizadores_{args.dataset}.png",
                              log=True)
        print(f"\nGráfica guardada en {ruta.relative_to(RAIZ)}")


def cmd_inicializacion(args):
    """Cómo influye la escala de los pesos iniciales en una red profunda."""
    X_train, _, y_train, _ = preparar("circulos")
    ocultas = (32,) * args.capas
    print(f"Red profunda: {args.capas} capas ocultas de 32 ({args.activacion}), "
          f"dataset 'circulos'\n")
    print("Desviación típica de las activaciones al inicio (capa 1 → última)"
          " y pérdida tras 30 épocas de SGD:\n")
    print(f"{'inicialización':<15} {'capa 1':>8} {'mitad':>8} {'última':>8} "
          f"{'pérdida inicial':>16} {'pérdida final':>14}")
    for nombre in INICIALIZACIONES:
        modelo = MLP(ocultas=ocultas, activacion=args.activacion,
                     inicializacion=nombre, epocas=30, tasa=0.05)
        modelo.construir(2)
        d = desviacion_activaciones(modelo, X_train)
        inicial = modelo.perdida(X_train, y_train.astype(float))
        modelo.entrenar(X_train, y_train)
        print(f"{nombre:<15} {d[0]:>8.3f} {d[len(d) // 2]:>8.3f} {d[-1]:>8.3f} "
              f"{inicial:>16.4f} {modelo.historial[-1]:>14.4f}")
    print("\nCon pesos diminutos ('pequena') la señal se apaga capa a capa, los"
          "\ngradientes también y la red no aprende (se queda en log 2 ≈ 0.693)."
          "\nXavier (tanh/sigmoide) y He (ReLU) mantienen la escala de la señal.")


def cmd_digitos(args):
    """MLP multiclase con softmax sobre el dataset digits (imágenes 8×8)."""
    X_train, X_test, y_train, y_test, escala = preparar_digitos(con_escala=True)
    ocultas = leer_ocultas(args.ocultas)
    modelo = MLP(ocultas=ocultas, activacion=args.activacion, optimizador=args.optimizador,
                 tasa=args.tasa, epocas=args.epocas, l2=args.l2,
                 inicializacion=args.init, validacion=0.2,
                 paciencia=args.paciencia or None)
    modelo.entrenar(X_train, y_train)
    pred = modelo.predecir(X_test)
    arquitectura = " -> ".join(str(n) for n in (64, *ocultas, 10))
    print(f"Dígitos 8×8: train {len(X_train)} (20 % de ellos para validación), "
          f"test {len(X_test)}")
    print(f"Arquitectura: {arquitectura} (softmax), {modelo.num_parametros()} parámetros")
    print(f"Optimizador: {modelo.optimizador} (tasa {modelo.tasa:g})")
    print(f"Épocas: {len(modelo.historial)} · mejor época en validación: "
          f"{modelo.mejor_epoca}")
    perdida = entropia_cruzada_categorica(y_test, modelo.probabilidades(X_test))
    print(f"Pérdida en test: {perdida:.4f}")
    print(f"Exactitud test: {exactitud(y_test, pred):.2%}\n")
    m = matriz_confusion_multiclase(y_test, pred, 10)
    print("Matriz de confusión (test):")
    print(formatear_matriz_multiclase(m))
    aciertos = np.diag(m) / m.sum(axis=1)
    print("\nExactitud por dígito: " + "  ".join(
        f"{d}:{a:.0%}" for d, a in enumerate(aciertos)))

    if args.graficas:
        ruta = grafica_curvas({"train": modelo.historial, "validación": modelo.historial_val},
                              "entropía cruzada", f"MLP en dígitos ({modelo.optimizador})",
                              CARPETA_GRAFICAS / "digitos_curvas.png",
                              marca=modelo.mejor_epoca)
        print(f"\nGráfica guardada en {ruta.relative_to(RAIZ)}")
        fallos = np.flatnonzero(pred != y_test)
        ruta = grafica_errores_digitos(X_test[fallos], y_test[fallos], pred[fallos],
                                       CARPETA_GRAFICAS / "digitos_errores.png")
        print(f"Gráfica guardada en {ruta.relative_to(RAIZ)}")
        ruta = grafica_pesos_digitos(modelo.densas()[0].W,
                                     CARPETA_GRAFICAS / "digitos_pesos.png")
        print(f"Gráfica guardada en {ruta.relative_to(RAIZ)}")

    if args.guardar:
        ruta = guardar_modelo(modelo, args.guardar, escala, info={
            "tipo": "digitos", "exactitud_test": exactitud(y_test, pred)})
        print(f"\nModelo guardado en {ruta}")


# --- Predecir con un modelo guardado -----------------------------------------

def leer_punto(texto):
    """'0.5,-1' -> array([0.5, -1.0])."""
    try:
        x, y = (float(v) for v in texto.split(","))
    except ValueError:
        raise ValueError(f"--punto debe ser 'x,y' con dos números (no {texto!r})") from None
    return np.array([x, y])


def barra(probabilidad, ancho=20):
    """Barra de texto proporcional a una probabilidad."""
    return "█" * int(round(probabilidad * ancho))


def mostrar_prediccion_digito(modelo, escala, pixeles, real=None):
    """Imprime el dígito en ASCII y las 3 clases más probables."""
    X = pixeles[None, :]
    if escala is not None:
        X = escala.transformar(X)
    p = modelo.probabilidades(X)[0]
    print(dibujo_ascii(pixeles))
    print()
    if real is not None:
        print(f"Dígito real: {real}")
    print(f"Predicción: {int(p.argmax())}  (confianza {p.max():.1%})")
    for clase in np.argsort(p)[::-1][:3]:
        print(f"  {clase}: {p[clase]:6.1%} {barra(p[clase])}")
    return int(p.argmax())


def cmd_predecir(args):
    """Carga un modelo .npz y lo usa con datos nuevos."""
    modelo, escala, info = cargar_modelo(args.modelo)
    n_entrada = modelo.densas()[0].W.shape[0]
    arquitectura = " -> ".join(str(n) for n in (n_entrada, *modelo.ocultas, modelo.n_salidas))
    print(f"Modelo {args.modelo}: {arquitectura} ({modelo.activacion}), "
          f"{modelo.num_parametros()} parámetros")
    if "exactitud_test" in info:
        print(f"Entrenado con '{info.get('dataset', 'digits')}', "
              f"exactitud en test al guardarlo: {info['exactitud_test']:.2%}")
    print()

    if n_entrada == 2:
        if args.indice is not None or args.dibujo:
            raise ValueError("Este modelo es de puntos 2D: usa --punto x,y")
        if not args.punto:
            print("Sin --punto: frontera de decisión en el espacio estandarizado "
                  "('#' = clase 1):")
            print(frontera_ascii(modelo))
            return 0
        X = np.array([leer_punto(t) for t in args.punto])
        p = modelo.probabilidades(escala.transformar(X) if escala else X)
        for (x, y), prob in zip(X, p):
            clase = int(prob >= 0.5)
            print(f"  ({x:+.2f}, {y:+.2f}) -> clase {clase}  "
                  f"P(clase 1) = {prob:.3f} {barra(prob)}")
        return 0

    if n_entrada == 64:
        if args.punto:
            raise ValueError("Este modelo es de dígitos: usa --indice o --dibujo")
        if args.dibujo:
            try:
                texto = Path(args.dibujo).read_text(encoding="utf-8")
            except OSError as error:
                raise ValueError(f"No se puede leer {args.dibujo}: {error}") from None
            mostrar_prediccion_digito(modelo, escala, leer_dibujo(texto))
            return 0
        _, X_test, _, y_test = dividir_digitos_crudos()
        indice = args.indice if args.indice is not None else 0
        if not 0 <= indice < len(X_test):
            raise ValueError(f"--indice debe estar entre 0 y {len(X_test) - 1}")
        print(f"Imagen de test nº {indice}:")
        mostrar_prediccion_digito(modelo, escala, X_test[indice], real=int(y_test[indice]))
        return 0

    raise ValueError(f"Modelo con {n_entrada} entradas: no sé qué datos darle")


# --- Comparación con scikit-learn ---------------------------------------------

def _cronometrar(funcion):
    inicio = time.perf_counter()
    resultado = funcion()
    return resultado, time.perf_counter() - inicio


def cmd_sklearn(args):
    """Nuestro MLP frente a MLPClassifier de scikit-learn con la misma configuración."""
    from sklearn.exceptions import ConvergenceWarning
    from sklearn.neural_network import MLPClassifier

    print("Misma arquitectura, mismo optimizador (Adam, tasa 0.01), lotes de 32.\n")
    print(f"{'dataset':<10} {'arquitectura':<18} {'numpy':>9} {'sklearn':>9} "
          f"{'t numpy':>9} {'t sklearn':>10}")
    casos = [(nombre, (16, 16), "tanh", False) for nombre in DATASETS]
    casos.append(("digitos", (32,), "relu", True))
    for nombre, ocultas, activacion, es_digitos in casos:
        if es_digitos:
            X_train, X_test, y_train, y_test = preparar_digitos()
        else:
            X_train, X_test, y_train, y_test = preparar(nombre, ruido=args.ruido)
        # En dígitos ambos usan validación (20 %) y parada temprana (paciencia 15)
        nuestro = MLP(ocultas=ocultas, activacion=activacion, optimizador="adam",
                      tasa=0.01, epocas=args.epocas,
                      inicializacion="he" if activacion == "relu" else "lecun",
                      validacion=0.2 if es_digitos else 0.0,
                      paciencia=15 if es_digitos else None)
        suyo = MLPClassifier(hidden_layer_sizes=ocultas,
                             activation="tanh" if activacion == "tanh" else "relu",
                             solver="adam", learning_rate_init=0.01, batch_size=32,
                             max_iter=args.epocas, alpha=0.0, random_state=42,
                             early_stopping=es_digitos, validation_fraction=0.2,
                             n_iter_no_change=15 if es_digitos else args.epocas)
        _, t_nuestro = _cronometrar(lambda: nuestro.entrenar(X_train, y_train))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ConvergenceWarning)
            _, t_suyo = _cronometrar(lambda: suyo.fit(X_train, y_train))
        arquitectura = "-".join(str(n) for n in (X_train.shape[1], *ocultas,
                                                 nuestro.n_salidas))
        print(f"{nombre:<10} {arquitectura:<18} "
              f"{exactitud(y_test, nuestro.predecir(X_test)):>9.2%} "
              f"{exactitud(y_test, suyo.predict(X_test)):>9.2%} "
              f"{t_nuestro:>8.2f}s {t_suyo:>9.2f}s")
    print("\nLas diferencias pequeñas vienen de la inicialización aleatoria, el"
          "\norden de los lotes y detalles de Adam/parada temprana: los dos hacen"
          "\nlo mismo por dentro (forward, backprop y un paso del optimizador).")


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
    p.add_argument("--optimizador", choices=list(OPTIMIZADORES), default="sgd")
    p.add_argument("--init", choices=list(INICIALIZACIONES), default="lecun",
                   help="inicialización de pesos (MLP)")
    p.add_argument("--validacion", type=float, default=0.0,
                   help="fracción de train apartada para validación (MLP)")
    p.add_argument("--paciencia", type=int,
                   help="épocas sin mejorar en validación antes de parar (MLP)")
    p.add_argument("--graficas", action="store_true",
                   help="guarda la frontera y la curva de aprendizaje en PNG")
    p.add_argument("--guardar", metavar="RUTA.npz",
                   help="guarda el MLP entrenado (pesos + estandarización)")
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

    p = sub.add_parser("optimizadores", help="compara SGD, momentum y Adam")
    p.add_argument("--dataset", choices=list(DATASETS), default="lunas")
    p.add_argument("--epocas", type=int, default=100)
    p.add_argument("--ruido", type=float, default=0.2)
    p.add_argument("--graficas", action="store_true")
    p.set_defaults(func=cmd_optimizadores)

    p = sub.add_parser("inicializacion", help="efecto de la inicialización de pesos")
    p.add_argument("--activacion", choices=list(ACTIVACIONES), default="tanh")
    p.add_argument("--capas", type=int, default=8, help="nº de capas ocultas")
    p.set_defaults(func=cmd_inicializacion)

    p = sub.add_parser("digitos", help="MLP con softmax en el dataset digits")
    p.add_argument("--ocultas", default="32")
    p.add_argument("--activacion", choices=list(ACTIVACIONES), default="relu")
    p.add_argument("--optimizador", choices=list(OPTIMIZADORES), default="adam")
    p.add_argument("--init", choices=list(INICIALIZACIONES), default="he")
    p.add_argument("--tasa", type=float)
    p.add_argument("--epocas", type=int, default=200)
    p.add_argument("--l2", type=float, default=0.0)
    p.add_argument("--paciencia", type=int, default=15,
                   help="parada temprana (0 = desactivada)")
    p.add_argument("--graficas", action="store_true")
    p.add_argument("--guardar", metavar="RUTA.npz", help="guarda el modelo entrenado")
    p.set_defaults(func=cmd_digitos)

    p = sub.add_parser("predecir", help="usa un modelo guardado con datos nuevos")
    p.add_argument("--modelo", required=True, help="fichero .npz guardado con --guardar")
    p.add_argument("--punto", action="append", metavar="X,Y",
                   help="punto 2D en coordenadas originales (se puede repetir)")
    p.add_argument("--indice", type=int, help="nº de imagen de test de digits")
    p.add_argument("--dibujo", help="fichero de texto con un dígito de 8×8 caracteres")
    p.set_defaults(func=cmd_predecir)

    p = sub.add_parser("sklearn", help="compara con MLPClassifier de scikit-learn")
    p.add_argument("--epocas", type=int, default=200)
    p.add_argument("--ruido", type=float, default=0.2)
    p.set_defaults(func=cmd_sklearn)
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
