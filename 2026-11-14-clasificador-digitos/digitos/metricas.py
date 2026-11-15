"""Métricas de evaluación calculadas a mano."""

import numpy as np


def exactitud(y_real, y_pred):
    """Fracción de predicciones correctas (accuracy), entre 0 y 1."""
    y_real = np.asarray(y_real)
    y_pred = np.asarray(y_pred)
    if y_real.shape != y_pred.shape:
        raise ValueError("y_real e y_pred deben tener la misma forma")
    if y_real.size == 0:
        raise ValueError("No hay ejemplos que evaluar")
    return float(np.mean(y_real == y_pred))


def matriz_confusion(y_real, y_pred, clases=None):
    """Matriz donde la fila es la clase real y la columna la clase predicha.

    La diagonal son los aciertos; todo lo que queda fuera son errores, y la
    posición dice qué dígito se confundió con cuál.
    """
    y_real = np.asarray(y_real)
    y_pred = np.asarray(y_pred)
    if clases is None:
        clases = np.unique(np.concatenate([y_real, y_pred]))
    posicion = {c: i for i, c in enumerate(clases)}
    matriz = np.zeros((len(clases), len(clases)), dtype=int)
    for real, pred in zip(y_real, y_pred):
        matriz[posicion[real], posicion[pred]] += 1
    return matriz


def formatear_matriz(matriz, clases):
    """Devuelve la matriz de confusión como texto alineado para la terminal."""
    ancho = max(3, len(str(matriz.max())) + 1)
    lineas = ["real\\pred " + "".join(f"{c:>{ancho}}" for c in clases)]
    for clase, fila in zip(clases, matriz):
        celdas = "".join(f"{(v if v else '.'):>{ancho}}" for v in fila)
        lineas.append(f"{clase:>9} {celdas}")
    return "\n".join(lineas)


def informe_por_clase(matriz):
    """Precisión, recall y F1 de cada clase a partir de la matriz de confusión.

    - precisión: de todas las veces que el modelo dijo "es un 8", ¿cuántas lo era?
      (aciertos de la clase / total de la columna)
    - recall (exhaustividad): de todos los 8 reales, ¿cuántos encontró?
      (aciertos de la clase / total de la fila)
    - F1: media armónica de las dos; solo es alta si ambas lo son.
    - soporte: cuántos ejemplos reales hay de esa clase.
    Devuelve un diccionario de arrays, con un valor por clase.
    """
    matriz = np.asarray(matriz, dtype=float)
    if matriz.ndim != 2 or matriz.shape[0] != matriz.shape[1]:
        raise ValueError("La matriz de confusión debe ser cuadrada")
    aciertos = np.diag(matriz)
    predichos = matriz.sum(axis=0)  # total por columna
    reales = matriz.sum(axis=1)     # total por fila
    # si una clase nunca se predice (o no aparece), su métrica se deja en 0
    precision = np.divide(aciertos, predichos, out=np.zeros_like(aciertos), where=predichos > 0)
    recall = np.divide(aciertos, reales, out=np.zeros_like(aciertos), where=reales > 0)
    suma = precision + recall
    f1 = np.divide(2 * precision * recall, suma, out=np.zeros_like(aciertos), where=suma > 0)
    return {"precision": precision, "recall": recall, "f1": f1, "soporte": reales.astype(int)}


def f1_macro(matriz):
    """Media del F1 de todas las clases (todas pesan igual)."""
    return float(np.mean(informe_por_clase(matriz)["f1"]))


def formatear_informe(informe, clases):
    """Tabla de texto con precisión, recall, F1 y soporte por clase."""
    lineas = [f"{'clase':>6} {'precisión':>10} {'recall':>8} {'F1':>8} {'soporte':>8}"]
    for i, clase in enumerate(clases):
        lineas.append(
            f"{clase:>6} {informe['precision'][i]:>10.2%} {informe['recall'][i]:>8.2%} "
            f"{informe['f1'][i]:>8.2%} {informe['soporte'][i]:>8}"
        )
    lineas.append(
        f"{'media':>6} {informe['precision'].mean():>10.2%} "
        f"{informe['recall'].mean():>8.2%} {informe['f1'].mean():>8.2%} "
        f"{informe['soporte'].sum():>8}"
    )
    return "\n".join(lineas)
