"""CLI del detector de spam.

Uso:
    python main.py generar [--n 1200] [--semilla 42]   # crea datos/mensajes.csv
    python main.py datos                               # resumen y ejemplos del dataset
    python main.py evaluar [--modelo bayes|logistica] [--repr bolsa|tfidf|...] [--grafica]
    python main.py predecir "texto del mensaje" [...] [--modelo ...] [--repr ...]
    python main.py comparar [--erratas 3] [--sklearn] [--grafica]
    python main.py validar [--modelo ...] [--repr ...] [--k 5] [--valores 0.1 1 10] [--grafica]
    python main.py curvas [--precision-min 0.99] [--grafica]
    python main.py explicar "texto del mensaje" [...] [--modelo ...] [--repr ...] [--n 12]
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

import numpy as np

from spam.datos import (ETIQUETAS, RUTA_CSV, cargar_csv, dividir_train_test, generar_mensajes,
                        guardar_csv, meter_erratas)
from spam.evaluacion import (VALORES_POR_DEFECTO, aplicar_umbral, auc_roc, buscar_hiperparametro,
                             curva_precision_recall, curva_roc, elegir_umbral, precision_media,
                             validacion_cruzada)
from spam.experimentos import (MODELOS, REPRESENTACIONES, comparar, entrenar, formatear_tabla,
                               verificar_con_sklearn)
from spam.explicacion import explicar, formatear_explicacion
from spam.logistica import RegresionLogistica
from spam.metricas import formatear_informe, informe
from spam.texto import tokenizar

CARPETA_GRAFICAS = Path(__file__).resolve().parent / "graficas"


def entrenar_modelo(textos_train, y_train, args=None):
    """Ajusta la representación y el modelo elegidos en la CLI (por defecto, bolsa de
    palabras + Naive Bayes, el modelo del día 1). Devuelve (vectorizador, modelo)."""
    if args is None:
        return entrenar(textos_train, y_train)
    return entrenar(textos_train, y_train, representacion=args.repr, modelo=args.modelo,
                    alfa=args.alfa, C=args.C)


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
    vec, modelo = entrenar_modelo(tx_train, y_train, args)
    parametro = f"alfa = {args.alfa}" if args.modelo == "bayes" else f"C = {args.C}"
    print(f"Modelo: {MODELOS[args.modelo][0]} · Representación: {REPRESENTACIONES[args.repr][0]}")
    print(f"Train: {len(tx_train)} mensajes · Test: {len(tx_test)} mensajes · "
          f"Vocabulario: {len(vec.vocabulario)} términos · {parametro}")
    if isinstance(modelo, RegresionLogistica):
        print(f"Descenso de gradiente: {modelo.iteraciones_} iteraciones, paso {modelo.tasa_:.2f},"
              f" pérdida final {modelo.historial_[-1]:.4f}")

    for nombre, textos, y in (("train", tx_train, y_train), ("test", tx_test, y_test)):
        pred = modelo.predecir(vec.transformar(textos))
        print(f"\nResultados en {nombre}:")
        print(formatear_informe(informe(y, pred)))

    # En los n-gramas de caracteres los espacios marcan inicio/fin de palabra: los
    # mostramos como "·" para que se vean.
    palabras = [p.replace(" ", "·") for p in vec.palabras]
    palabras_spam, palabras_ham = modelo.palabras_mas_indicativas(palabras, n=10)
    medida = ("log P(w|spam) - log P(w|ham)" if args.modelo == "bayes"
              else "peso aprendido w")
    print(f"\nTérminos que más delatan al spam ({medida}):")
    print("  " + ", ".join(f"{p} ({r:+.1f})" for p, r in palabras_spam))
    print("Términos más típicos de ham:")
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
        if args.modelo == "bayes":
            ruta = guardar_grafica_palabras(palabras_spam, palabras_ham)
        else:
            ruta = guardar_grafica_perdida(modelo)
        print(f"\nGráfica guardada en {ruta}")


def cmd_predecir(args):
    textos, y = cargar_csv(Path(args.csv))
    vec, modelo = entrenar_modelo(textos, y, args)  # usa todos los datos
    proba = modelo.predecir_proba(vec.transformar(args.mensajes))[:, 1]
    for texto, p in zip(args.mensajes, proba):
        etiqueta = "SPAM" if p >= args.umbral else "ham "
        print(f"[{etiqueta}] P(spam) = {p:.3f}  ·  {texto}")
        conocidas = [t for t in vec.terminos(texto) if t in vec.vocabulario]
        if args.repr == "tfidf-caracteres":  # demasiados trozos para listarlos todos
            print(f"         términos conocidos: {len(conocidas)}")
        else:
            print(f"         términos usados: {' | '.join(conocidas) or '(ninguno conocido)'}")


def cmd_explicar(args):
    textos, y = cargar_csv(Path(args.csv))
    vec, modelo = entrenar_modelo(textos, y, args)  # usa todos los datos, como predecir
    print(f"Modelo: {MODELOS[args.modelo][0]} · Representación: {REPRESENTACIONES[args.repr][0]}")
    print("Contribución de cada término a los log-odds = log(P(spam) / P(ham)); "
          "█ empuja a spam, ░ a ham.")
    for texto in args.mensajes:
        exp = explicar(vec, modelo, texto)
        etiqueta = "SPAM" if exp["proba"] >= args.umbral else "ham"
        print(f"\n«{texto}»  →  {etiqueta}")
        print(formatear_explicacion(exp, n=args.n))


def _nombre_param(modelo: str) -> str:
    return "alfa" if modelo == "bayes" else "C"


def cmd_validar(args):
    tx_train, tx_test, y_train, y_test = preparar(args)
    nombre = _nombre_param(args.modelo)
    valores = args.valores or VALORES_POR_DEFECTO[args.modelo]
    print(f"Modelo: {MODELOS[args.modelo][0]} · Representación: {REPRESENTACIONES[args.repr][0]}")
    print(f"Validación cruzada estratificada con k = {args.k} pliegues, SOLO sobre los "
          f"{len(tx_train)} mensajes de train.\n")
    filas, mejor = buscar_hiperparametro(tx_train, y_train, args.repr, args.modelo, valores,
                                         k=args.k, semilla=args.semilla)
    print(f"{nombre:>7s}  {'exactitud':>15s}  {'precisión':>15s}  {'recall':>15s}  {'F1':>15s}")
    for f in filas:
        celdas = "  ".join(f"{f['media'][c]:.3f} ± {f['desviacion'][c]:.3f}".rjust(15)
                           for c in ("exactitud", "precision", "recall", "f1"))
        marca = "  ← mejor" if f["valor"] == mejor else ""
        print(f"{f['valor']:7g}  {celdas}{marca}")

    # Con el mejor valor: entrenar con TODO el train y medir UNA vez en test.
    params = {"alfa": mejor} if args.modelo == "bayes" else {"C": mejor}
    vec, modelo = entrenar(tx_train, y_train, args.repr, args.modelo, **params)
    inf = informe(y_test, modelo.predecir(vec.transformar(tx_test)))
    print(f"\nMejor {nombre} = {mejor:g} (con empate se elige el modelo más sencillo). "
          f"Resultado en test:")
    print(formatear_informe(inf))

    if args.grafica:
        ruta = guardar_grafica_validacion(filas, mejor, args)
        print(f"\nGráfica guardada en {ruta}")


# Configuraciones que se comparan en «curvas» (representación, modelo, etiqueta).
CONFIG_CURVAS = [
    ("bolsa", "bayes", "Bayes · bolsa"),
    ("tfidf", "logistica", "logística · TF-IDF"),
    ("tfidf-caracteres", "logistica", "logística · caracteres"),
]


def cmd_curvas(args):
    tx_train, tx_test, y_train, y_test = preparar(args)
    print(f"Probabilidades de validación: «fuera de pliegue» con k = {args.k} dentro de train.")
    print("AUC-ROC: probabilidad de que un spam puntúe más que un ham. "
          "AP: precisión media (área bajo la curva PR).\n")
    print(f"{'configuración':24s} {'AUC val.':>8s} {'AP val.':>8s} {'AUC test':>8s} {'AP test':>8s}")
    curvas = []
    for repr_, modelo, etiqueta in CONFIG_CURVAS:
        oof = validacion_cruzada(tx_train, y_train, repr_, modelo, alfa=args.alfa, C=args.C,
                                 k=args.k, semilla=args.semilla)["proba_oof"]
        vec, mod = entrenar(tx_train, y_train, repr_, modelo, alfa=args.alfa, C=args.C)
        p_test = mod.predecir_proba(vec.transformar(tx_test))[:, 1]
        print(f"{etiqueta:24s} {auc_roc(y_train, oof):8.3f} {precision_media(y_train, oof):8.3f} "
              f"{auc_roc(y_test, p_test):8.3f} {precision_media(y_test, p_test):8.3f}")
        curvas.append({"etiqueta": etiqueta, "repr": repr_, "modelo": modelo,
                       "oof": oof, "test": p_test})

    # Ajuste del umbral: se elige con las probabilidades de validación y se comprueba en test.
    elegida = next((c for c in curvas if (c["repr"], c["modelo"]) == (args.repr, args.modelo)),
                   None)
    if elegida is None:  # otra combinación: la calculamos aparte
        oof = validacion_cruzada(tx_train, y_train, args.repr, args.modelo, alfa=args.alfa,
                                 C=args.C, k=args.k, semilla=args.semilla)["proba_oof"]
        vec, mod = entrenar(tx_train, y_train, args.repr, args.modelo, alfa=args.alfa, C=args.C)
        elegida = {"etiqueta": f"{args.modelo} · {args.repr}", "oof": oof,
                   "test": mod.predecir_proba(vec.transformar(tx_test))[:, 1]}
    print(f"\nAjuste del umbral para «{elegida['etiqueta']}»:")
    umbral_f1, _ = elegir_umbral(y_train, elegida["oof"])
    umbral_p, info_p = elegir_umbral(y_train, elegida["oof"], precision_minima=args.precision_min)
    print(f"{'umbral':>26s} {'prec. val':>9s} {'rec. val':>8s} │ {'prec. test':>10s} "
          f"{'rec. test':>9s} {'F1 test':>7s} {'FP':>3s} {'FN':>3s}")
    opciones = [(f"{u:g}", u) for u in (0.1, 0.3, 0.5, 0.7, 0.9)]
    opciones += [(f"máx. F1 → {umbral_f1:.3f}", umbral_f1),
                 (f"prec. ≥ {args.precision_min:g} → {umbral_p:.3f}", umbral_p)]
    for nombre, u in opciones:
        v = informe(y_train, aplicar_umbral(elegida["oof"], u))
        t = informe(y_test, aplicar_umbral(elegida["test"], u))
        print(f"{nombre:>26s} {v['precision']:9.3f} {v['recall']:8.3f} │ "
              f"{t['precision']:10.3f} {t['recall']:9.3f} {t['f1']:7.3f} "
              f"{t['falsos_positivos']:3d} {t['falsos_negativos']:3d}")
    if info_p["recall"] < 0.5:
        print(f"Aviso: para llegar a precisión {args.precision_min:g} hay que renunciar a casi todo "
              f"el spam (recall {info_p['recall']:.2f}). Con un 3 % de etiquetas mal puestas, "
              "parte de los «falsos positivos» son en realidad spam etiquetado como ham.")
    print("FP = mensajes buenos enviados a spam · FN = spam que se cuela en la bandeja.")

    if args.grafica:
        ruta = guardar_grafica_curvas(curvas, y_test, elegida, umbral_p)
        print(f"\nGráfica guardada en {ruta}")


def cmd_comparar(args):
    tx_train, tx_test, y_train, y_test = preparar(args)
    tx_erratas = meter_erratas(tx_test, args.erratas, semilla=args.semilla) if args.erratas else None
    print(f"Train: {len(tx_train)} · Test: {len(tx_test)} · alfa (Bayes) = {args.alfa} · "
          f"C (logística) = {args.C}")
    if tx_erratas:
        print(f"«F1 errat.» = F1 en el mismo test con {args.erratas} erratas extra por mensaje.")
    print()
    filas = comparar(tx_train, y_train, tx_test, y_test, alfa=args.alfa, C=args.C,
                     tx_test_erratas=tx_erratas)
    print(formatear_tabla(filas))

    if args.sklearn:
        print("\nVerificación contra scikit-learn (TF-IDF de palabras + regresión logística):")
        r = verificar_con_sklearn(tx_train, y_train, tx_test, C=args.C)
        print(f"  TF-IDF: diferencia máxima con TfidfVectorizer      = {r['tfidf_dif_max']:.1e}")
        print(f"  Logística: diferencia máxima en P(spam)             = "
              f"{r['logistica_proba_dif_max']:.1e}")
        print(f"  Logística: diferencia máxima en los pesos           = "
              f"{r['logistica_pesos_dif_max']:.1e}")
        print(f"  Logística: predicciones iguales                     = "
              f"{r['logistica_predicciones_iguales']:.0%}  ({r['logistica_iteraciones']} iteraciones)")

    if args.grafica:
        ruta = guardar_grafica_comparacion(filas)
        print(f"\nGráfica guardada en {ruta}")


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


def guardar_grafica_perdida(modelo) -> Path:
    """Curva de aprendizaje: cómo baja la pérdida J en cada paso del descenso de gradiente."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 3.5), dpi=90)
    ax.plot(range(1, len(modelo.historial_) + 1), modelo.historial_, color="#8e44ad")
    ax.set_xscale("log")
    ax.set_xlabel("iteración (escala log)")
    ax.set_ylabel("pérdida J (log-loss + L2)")
    ax.set_title(f"Regresión logística: descenso de gradiente (C = {modelo.C:g})")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    CARPETA_GRAFICAS.mkdir(exist_ok=True)
    ruta = CARPETA_GRAFICAS / "perdida_logistica.png"
    fig.savefig(ruta)
    plt.close(fig)
    return ruta


def guardar_grafica_comparacion(filas) -> Path:
    """Barras de F1 por combinación: test normal y test con erratas."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    etiquetas = [f"{f['representacion']}\n{f['modelo']}" for f in filas]
    x = np.arange(len(filas))
    ancho = 0.4 if "f1_erratas" in filas[0] else 0.7
    fig, ax = plt.subplots(figsize=(8, 4), dpi=90)
    ax.bar(x - (ancho / 2 if ancho < 0.7 else 0), [f["f1"] for f in filas], ancho,
           label="test", color="#2e86c1")
    if "f1_erratas" in filas[0]:
        ax.bar(x + ancho / 2, [f["f1_erratas"] for f in filas], ancho,
               label="test con erratas", color="#e67e22")
    ax.set_xticks(x, etiquetas, fontsize=7)
    minimo = min(min(f["f1"], f.get("f1_erratas", 1)) for f in filas)
    ax.set_ylim(max(0.0, minimo - 0.05), 1.0)
    ax.set_ylabel("F1 (spam)")
    ax.set_title("Representación × modelo")
    ax.legend(loc="upper right", ncol=2)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    CARPETA_GRAFICAS.mkdir(exist_ok=True)
    ruta = CARPETA_GRAFICAS / "comparacion_modelos.png"
    fig.savefig(ruta)
    plt.close(fig)
    return ruta


def guardar_grafica_validacion(filas, mejor, args) -> Path:
    """Curva de validación: F1 media (± desviación) frente al hiperparámetro."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    valores = [f["valor"] for f in filas]
    medias = np.array([f["media"]["f1"] for f in filas])
    desv = np.array([f["desviacion"]["f1"] for f in filas])
    fig, ax = plt.subplots(figsize=(6, 3.5), dpi=90)
    ax.plot(valores, medias, "o-", color="#2e86c1", label="F1 media (validación)")
    ax.fill_between(valores, medias - desv, medias + desv, color="#2e86c1", alpha=0.2,
                    label="± 1 desviación")
    ax.axvline(mejor, color="#c0392b", linestyle="--", linewidth=1, label=f"elegido = {mejor:g}")
    ax.set_xscale("log")
    ax.set_xlabel(_nombre_param(args.modelo) + " (escala log)")
    ax.set_ylabel("F1 (spam)")
    ax.set_title(f"Validación cruzada ({args.k} pliegues): {MODELOS[args.modelo][0]}")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    CARPETA_GRAFICAS.mkdir(exist_ok=True)
    ruta = CARPETA_GRAFICAS / f"validacion_{args.modelo}.png"
    fig.savefig(ruta)
    plt.close(fig)
    return ruta


def guardar_grafica_curvas(curvas, y_test, elegida, umbral) -> Path:
    """Curvas ROC y precisión-recall en test, con el umbral elegido marcado."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colores = ["#2e86c1", "#8e44ad", "#e67e22"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4), dpi=90)
    for c, color in zip(curvas, colores):
        tfp, tvp, _ = curva_roc(y_test, c["test"])
        ax1.plot(tfp, tvp, color=color, label=f"{c['etiqueta']} (AUC {auc_roc(y_test, c['test']):.3f})")
        prec, rec, _ = curva_precision_recall(y_test, c["test"])
        ax2.step(rec, prec, where="post", color=color,
                 label=f"{c['etiqueta']} (AP {precision_media(y_test, c['test']):.3f})")
    ax1.plot([0, 1], [0, 1], ":", color="#999", label="azar (AUC 0.5)")
    # Punto de funcionamiento con el umbral elegido.
    inf = informe(y_test, aplicar_umbral(elegida["test"], umbral))
    m = inf["matriz"]
    ax1.plot(m[0, 1] / m[0].sum(), inf["recall"], "o", color="#c0392b", label=f"umbral {umbral:.2f}")
    ax2.plot(inf["recall"], inf["precision"], "o", color="#c0392b", label=f"umbral {umbral:.2f}")
    ax1.set_xlabel("tasa de falsos positivos (ham → spam)")
    ax1.set_ylabel("recall (spam cazado)")
    ax1.set_title("Curva ROC (test)")
    ax2.set_xlabel("recall")
    ax2.set_ylabel("precisión")
    ax2.set_title("Curva precisión-recall (test)")
    ax2.set_ylim(0.5, 1.02)
    for ax in (ax1, ax2):
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7, loc="lower right" if ax is ax1 else "lower left")
    fig.tight_layout()
    CARPETA_GRAFICAS.mkdir(exist_ok=True)
    ruta = CARPETA_GRAFICAS / "curvas_roc_pr.png"
    fig.savefig(ruta)
    plt.close(fig)
    return ruta


# --- Argumentos ------------------------------------------------------------

def crear_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Detector de spam con PLN hecho a mano (Naive Bayes y regresión logística)")
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

    def opciones_modelo(sp):
        sp.add_argument("--modelo", choices=list(MODELOS), default="bayes")
        sp.add_argument("--repr", choices=list(REPRESENTACIONES), default="bolsa",
                        help="representación del texto")
        sp.add_argument("--alfa", type=float, default=1.0, help="suavizado de Laplace (Bayes)")
        sp.add_argument("--C", type=float, default=10.0,
                        help="inversa de la regularización L2 (logística)")

    def opciones_division(sp):
        sp.add_argument("--test", type=float, default=0.25, help="proporción de test")
        sp.add_argument("--semilla", type=int, default=0)

    e = sub.add_parser("evaluar", help="entrena en train y evalúa en test")
    opciones_modelo(e)
    opciones_division(e)
    e.add_argument("--grafica", action="store_true",
                   help="guarda un PNG (palabras clave en Bayes, curva de pérdida en logística)")
    e.set_defaults(func=cmd_evaluar)

    def opcion_umbral(sp):
        sp.add_argument("--umbral", type=float, default=0.5,
                        help="P(spam) a partir de la cual se marca como spam")

    pr = sub.add_parser("predecir", help="clasifica mensajes nuevos")
    pr.add_argument("mensajes", nargs="+")
    opciones_modelo(pr)
    opcion_umbral(pr)
    pr.set_defaults(func=cmd_predecir)

    ex = sub.add_parser("explicar", help="desglosa qué palabras deciden la predicción")
    ex.add_argument("mensajes", nargs="+")
    opciones_modelo(ex)
    opcion_umbral(ex)
    ex.add_argument("--n", type=int, default=12, help="términos a mostrar")
    ex.set_defaults(func=cmd_explicar)

    v = sub.add_parser("validar", help="validación cruzada y búsqueda de alfa / C")
    opciones_modelo(v)
    opciones_division(v)
    v.add_argument("--k", type=int, default=5, help="número de pliegues")
    v.add_argument("--valores", type=float, nargs="+",
                   help="valores de alfa (Bayes) o C (logística) a probar")
    v.add_argument("--grafica", action="store_true", help="guarda la curva de validación")
    v.set_defaults(func=cmd_validar)

    cu = sub.add_parser("curvas", help="curvas ROC/PR, AUC y ajuste del umbral")
    opciones_modelo(cu)
    cu.set_defaults(modelo="logistica", repr="tfidf")
    opciones_division(cu)
    cu.add_argument("--k", type=int, default=5, help="número de pliegues")
    cu.add_argument("--precision-min", type=float, default=0.96,
                    help="precisión mínima exigida al elegir el umbral")
    cu.add_argument("--grafica", action="store_true", help="guarda las curvas en PNG")
    cu.set_defaults(func=cmd_curvas)

    c = sub.add_parser("comparar", help="tabla de todas las representaciones × modelos")
    c.add_argument("--alfa", type=float, default=1.0, help="suavizado de Laplace (Bayes)")
    c.add_argument("--C", type=float, default=10.0, help="regularización (logística)")
    c.add_argument("--erratas", type=int, default=3,
                   help="erratas extra por mensaje para medir robustez (0 = no medir)")
    c.add_argument("--sklearn", action="store_true", help="verifica TF-IDF y logística con sklearn")
    c.add_argument("--grafica", action="store_true", help="guarda un PNG con la comparación")
    opciones_division(c)
    c.set_defaults(func=cmd_comparar)
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
