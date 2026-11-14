"""Tests del clasificador de dígitos. Ejecutar con: python -m pytest"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from digitos.datos import cargar_digitos, dividir_train_test, normalizar, preparar_datos
from digitos.knn import ClasificadorKNN, distancias_euclideas
from digitos.metricas import exactitud, formatear_matriz, matriz_confusion
from digitos.visual import barra, digito_ascii
import main as cli


# ---------- datos ----------

def test_cargar_digitos_forma():
    X, y = cargar_digitos()
    assert X.shape == (1797, 64)
    assert set(y) == set(range(10))


def test_normalizar_rango():
    X, _ = cargar_digitos()
    Xn = normalizar(X)
    assert Xn.min() == 0 and Xn.max() == 1


def test_division_sin_solapamiento_y_reproducible():
    X = np.arange(200).reshape(100, 2)  # cada fila es única
    y = np.repeat([0, 1], 50)
    a = dividir_train_test(X, y, 0.2, semilla=1)
    b = dividir_train_test(X, y, 0.2, semilla=1)
    X_train, X_test, y_train, y_test = a
    assert len(X_train) == 80 and len(X_test) == 20
    assert not set(map(tuple, X_train)) & set(map(tuple, X_test))
    assert all(np.array_equal(p, q) for p, q in zip(a, b))
    # estratificada: 10 de cada clase en test
    assert (y_test == 0).sum() == 10 and (y_test == 1).sum() == 10
    # las etiquetas siguen emparejadas con sus filas
    assert np.array_equal(y_train, (X_train[:, 0] >= 100).astype(int))


def test_division_proporcion_invalida():
    with pytest.raises(ValueError):
        dividir_train_test(np.zeros((4, 1)), np.zeros(4), 1.5)


# ---------- k-NN ----------

def test_distancias_euclideas():
    d = distancias_euclideas([[0, 0], [3, 4]], [[0, 0], [6, 8]])
    assert np.allclose(d, [[0, 10], [5, 5]])


def test_knn_caso_sencillo():
    X = [[0, 0], [0, 1], [1, 0], [10, 10], [10, 11], [11, 10]]
    y = [0, 0, 0, 1, 1, 1]
    modelo = ClasificadorKNN(k=3).entrenar(X, y)
    assert list(modelo.predecir([[0.2, 0.2], [9, 9]])) == [0, 1]
    assert np.allclose(modelo.predecir_proba([[0.2, 0.2]]), [[1, 0]])


def test_knn_k1_acierta_el_entrenamiento():
    X_train, _, y_train, _ = preparar_datos()
    modelo = ClasificadorKNN(k=1).entrenar(X_train, y_train)
    assert exactitud(y_train[:200], modelo.predecir(X_train[:200])) >= 0.99


def test_knn_empate_gana_el_mas_cercano():
    # k=2 con un voto para cada clase: debe ganar la del vecino más próximo
    modelo = ClasificadorKNN(k=2).entrenar([[0.0], [3.0]], [5, 2])
    assert modelo.predecir([[2.5]])[0] == 2
    assert modelo.predecir([[0.5]])[0] == 5


def test_knn_errores():
    with pytest.raises(ValueError):
        ClasificadorKNN(k=0)
    with pytest.raises(RuntimeError):
        ClasificadorKNN().predecir([[1, 2]])
    with pytest.raises(ValueError):
        ClasificadorKNN(k=5).entrenar([[1], [2]], [0, 1])
    modelo = ClasificadorKNN(k=1).entrenar([[1, 2]], [0])
    with pytest.raises(ValueError):
        modelo.predecir([[1, 2, 3]])


def test_knn_igual_que_scikit_learn():
    from sklearn.neighbors import KNeighborsClassifier

    X_train, X_test, y_train, y_test = preparar_datos()
    propio = ClasificadorKNN(k=1).entrenar(X_train, y_train).predecir(X_test)
    referencia = KNeighborsClassifier(n_neighbors=1).fit(X_train, y_train).predict(X_test)
    assert np.mean(propio == referencia) >= 0.995


def test_knn_exactitud_minima_en_test():
    X_train, X_test, y_train, y_test = preparar_datos()
    modelo = ClasificadorKNN(k=3).entrenar(X_train, y_train)
    assert exactitud(y_test, modelo.predecir(X_test)) > 0.95


# ---------- métricas ----------

def test_exactitud():
    assert exactitud([1, 2, 3, 4], [1, 2, 0, 0]) == 0.5
    with pytest.raises(ValueError):
        exactitud([], [])


def test_matriz_confusion():
    m = matriz_confusion([0, 0, 1, 1, 1], [0, 1, 1, 1, 0], clases=[0, 1])
    assert m.tolist() == [[1, 1], [1, 2]]
    assert m.sum() == 5
    assert "real\\pred" in formatear_matriz(m, [0, 1])


# ---------- visual y CLI ----------

def test_digito_ascii():
    dibujo = digito_ascii(np.linspace(0, 1, 64))
    lineas = dibujo.split("\n")
    assert len(lineas) == 8 and all(len(l) == 16 for l in lineas)
    assert dibujo[0] == " " and dibujo[-1] == "@"


def test_barra():
    assert barra(0.5, 4) == "██░░"


def test_cli_evaluar(capsys):
    cli.main(["evaluar", "--k", "3"])
    assert "Exactitud en test" in capsys.readouterr().out


def test_cli_ver_indice_invalido():
    with pytest.raises(SystemExit):
        cli.main(["ver", "--indice", "99999"])
