"""Explicar una predicción: ¿qué palabras empujan el mensaje hacia spam o hacia ham?

Los dos modelos del proyecto son LINEALES en el espacio de los "log-odds"
(logaritmo de P(spam)/P(ham)), así que la explicación es exacta, no aproximada:

  Regresión logística:  log-odds = b + Σ x_j · w_j
  Naive Bayes:          log-odds = log P(spam)/P(ham) + Σ x_j · [log P(j|spam) − log P(j|ham)]

Cada sumando x_j · (peso del término j) es la CONTRIBUCIÓN del término j: positiva
empuja hacia spam, negativa hacia ham. El término constante (sesgo o "prior") es lo
que el modelo pensaría de un mensaje vacío. Sumándolo todo y pasándolo por la
sigmoide sale exactamente la P(spam) que da el modelo.

Con n-gramas de caracteres hay miles de trozos tipo "gra", "rat"… Para que se pueda
leer, el reparto se agrupa por palabra: cada trozo reparte su contribución a partes
iguales entre las palabras en las que aparece.
"""

from collections import Counter, defaultdict

import numpy as np

from .bayes import NaiveBayesMultinomial
from .logistica import RegresionLogistica, sigmoide
from .texto import tokenizar
from .vectorizador import ngramas_caracteres


def pesos_lineales(modelo):
    """(constante, vector de pesos) tales que log-odds = constante + x · pesos."""
    if isinstance(modelo, RegresionLogistica):
        modelo._comprobar()
        return float(modelo.b_), modelo.w_
    if isinstance(modelo, NaiveBayesMultinomial):
        modelo._comprobar()
        if len(modelo.clases_) != 2:
            raise ValueError("Solo se pueden explicar modelos binarios")
        return (float(modelo.log_prior_[1] - modelo.log_prior_[0]),
                modelo.log_verosimilitud_[1] - modelo.log_verosimilitud_[0])
    raise TypeError(f"No sé explicar modelos de tipo {type(modelo).__name__}")


def _es_de_caracteres(vec) -> bool:
    bolsa = getattr(vec, "bolsa", vec)
    return bolsa.analizador == "caracter"


def explicar(vec, modelo, texto: str) -> dict:
    """Desglosa la predicción de un mensaje.

    Devuelve un dict con:
      constante      sesgo / log-prior (lo que se piensa sin ver ninguna palabra)
      contribuciones lista de (término o palabra, contribución), de mayor a menor |valor|
      log_odds       constante + suma de contribuciones
      proba          sigmoide(log_odds) = P(spam)
      desconocidos   términos del mensaje que no estaban en el vocabulario (no cuentan)
    """
    constante, pesos = pesos_lineales(modelo)
    x = vec.transformar([texto])[0]
    contrib_termino = x * pesos  # contribución exacta de cada columna
    palabras_vocab = vec.palabras

    if _es_de_caracteres(vec):
        contribuciones, desconocidos = _agrupar_por_palabra(vec, texto, contrib_termino)
    else:
        contribuciones = [(palabras_vocab[j], float(contrib_termino[j]))
                          for j in np.flatnonzero(x)]
        desconocidos = sorted({t for t in vec.terminos(texto) if t not in vec.vocabulario})

    contribuciones.sort(key=lambda tc: -abs(tc[1]))
    log_odds = constante + float(contrib_termino.sum())
    return {
        "constante": constante,
        "contribuciones": contribuciones,
        "log_odds": log_odds,
        "proba": float(sigmoide(np.array([log_odds]))[0]),
        "desconocidos": desconocidos,
    }


def _agrupar_por_palabra(vec, texto, contrib_termino):
    """Reparte la contribución de cada n-grama de caracteres entre sus apariciones
    y suma por palabra. La suma total no cambia (el reparto es exacto)."""
    bolsa = vec.bolsa
    n_min, n_max = bolsa.ngramas
    palabras = tokenizar(texto, quitar_vacias=False)
    trozos_por_palabra = [ngramas_caracteres(p, n_min, n_max) for p in palabras]
    apariciones = Counter(t for trozos in trozos_por_palabra for t in trozos)
    por_palabra = defaultdict(float)
    desconocidas = []
    for palabra, trozos in zip(palabras, trozos_por_palabra):
        conocidos = [t for t in trozos if t in bolsa.vocabulario]
        if not conocidos:
            desconocidas.append(palabra)
            continue
        for t in conocidos:
            por_palabra[palabra] += contrib_termino[bolsa.vocabulario[t]] / apariciones[t]
    return [(p, float(c)) for p, c in por_palabra.items()], sorted(set(desconocidas))


def formatear_explicacion(exp: dict, n: int = 12, ancho: int = 24) -> str:
    """Texto con barras: ████ hacia spam (+), ░░░░ hacia ham (−)."""
    contribs = exp["contribuciones"][:n]
    maximo = max([abs(c) for _, c in contribs] + [abs(exp["constante"]), 1e-9])
    lineas = [f"  {'(punto de partida)':22s} {exp['constante']:+7.2f}"]
    for termino, c in contribs:
        largo = max(1, int(round(abs(c) / maximo * ancho))) if c else 0
        barra = ("█" if c > 0 else "░") * largo
        lineas.append(f"  {termino.replace(' ', '·')[:22]:22s} {c:+7.2f}  {barra}")
    resto = exp["contribuciones"][n:]
    if resto:
        lineas.append(f"  {f'(otros {len(resto)})':22s} {sum(c for _, c in resto):+7.2f}")
    lineas.append(f"  {'= log-odds':22s} {exp['log_odds']:+7.2f}  →  P(spam) = {exp['proba']:.3f}")
    if exp["desconocidos"]:
        lineas.append("  Sin peso (no vistas al entrenar): " + ", ".join(exp["desconocidos"][:10]))
    return "\n".join(lineas)
