"""Guardar y cargar un MLP entrenado en un fichero .npz de numpy.

Un modelo entrenado no es más que:
  - su "receta" (arquitectura e hiperparámetros) -> se guarda como JSON,
  - sus números (W y b de cada capa densa)        -> arrays de numpy,
  - la estandarización usada al entrenar (media y desviación de train).

Lo último es fácil de olvidar y es un error clásico: si al predecir no se
aplica exactamente la misma transformación que al entrenar, el modelo recibe
datos en otra escala y sus predicciones no valen nada.
"""

import json
from pathlib import Path

import numpy as np

from .datos import Estandarizador
from .mlp import MLP

VERSION_FORMATO = 1

# Hiperparámetros que se guardan para poder reconstruir el MLP
_CAMPOS = ("ocultas", "activacion", "tasa", "epocas", "tam_lote", "l2", "semilla",
           "optimizador", "inicializacion")


def guardar_modelo(modelo, ruta, escala=None, info=None):
    """Guarda `modelo` (MLP entrenado) en `ruta` (.npz).

    `escala`: Estandarizador ajustado con train (opcional pero recomendable).
    `info`: diccionario con datos extra (dataset, exactitud en test...).
    """
    if not isinstance(modelo, MLP):
        raise ValueError("Solo se pueden guardar modelos MLP")
    modelo._comprobar_entrenado()
    ruta = Path(ruta)
    if ruta.suffix != ".npz":
        ruta = ruta.with_suffix(".npz")
    ruta.parent.mkdir(parents=True, exist_ok=True)

    receta = {campo: getattr(modelo, campo) for campo in _CAMPOS}
    receta["ocultas"] = list(modelo.ocultas)
    meta = {
        "version": VERSION_FORMATO,
        "receta": receta,
        "n_entrada": int(modelo.densas()[0].W.shape[0]),
        "n_salidas": int(modelo.n_salidas),
        "mejor_epoca": modelo.mejor_epoca,
        "epocas_hechas": len(modelo.historial),
        "info": info or {},
    }
    arrays = {"meta": np.array(json.dumps(meta))}
    for i, capa in enumerate(modelo.densas()):
        arrays[f"W{i}"] = capa.W
        arrays[f"b{i}"] = capa.b
    if escala is not None:
        if escala.media is None:
            raise ValueError("El estandarizador no está ajustado")
        arrays["media"] = escala.media
        arrays["desviacion"] = escala.desviacion
    np.savez_compressed(ruta, **arrays)
    return ruta


def cargar_modelo(ruta):
    """Carga un .npz guardado con `guardar_modelo`.

    Devuelve (modelo, escala, info). `escala` es None si no se guardó.
    """
    ruta = Path(ruta)
    if not ruta.exists():
        raise ValueError(f"No existe el fichero {ruta}")
    try:
        # allow_pickle=False: un .npz nunca debe poder ejecutar código al cargarse
        with np.load(ruta, allow_pickle=False) as datos:
            contenido = {clave: datos[clave] for clave in datos.files}
    except (OSError, ValueError) as error:
        raise ValueError(f"{ruta} no es un modelo válido ({error})") from None
    if "meta" not in contenido:
        raise ValueError(f"{ruta} no es un modelo de red-neuronal-numpy")

    meta = json.loads(str(contenido["meta"]))
    if meta.get("version") != VERSION_FORMATO:
        raise ValueError(f"Versión de formato no soportada: {meta.get('version')}")

    modelo = MLP(**meta["receta"])
    modelo.construir(meta["n_entrada"], meta["n_salidas"])
    densas = modelo.densas()
    for i, capa in enumerate(densas):
        W, b = contenido.get(f"W{i}"), contenido.get(f"b{i}")
        if W is None or W.shape != capa.W.shape or b.shape != capa.b.shape:
            raise ValueError(f"Los pesos de la capa {i} no cuadran con la arquitectura")
        capa.W, capa.b = W.astype(float), b.astype(float)
    modelo.mejor_epoca = meta.get("mejor_epoca")

    escala = None
    if "media" in contenido:
        escala = Estandarizador()
        escala.media = contenido["media"]
        escala.desviacion = contenido["desviacion"]
    return modelo, escala, meta.get("info", {})
