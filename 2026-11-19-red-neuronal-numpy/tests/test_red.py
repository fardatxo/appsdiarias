"""Tests de red-neuronal-numpy (día 1: datos, métricas y modelos lineales)."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main  # noqa: E402
from red.datos import DATASETS, Estandarizador, dividir, generar, preparar  # noqa: E402
from red.lineales import Perceptron, RegresionLogistica, sigmoide  # noqa: E402
from red.metricas import (  # noqa: E402
    entropia_cruzada_binaria,
    exactitud,
    matriz_confusion,
    precision_recall_f1,
)
from red.visual import frontera_ascii  # noqa: E402


# --- Datos ---------------------------------------------------------------

@pytest.mark.parametrize("nombre", list(DATASETS))
def test_generar_forma_y_etiquetas(nombre):
    X, y = generar(nombre, n=100)
    assert X.shape == (100, 2)
    assert set(np.unique(y)) == {0, 1}


def test_generar_es_reproducible():
    X1, y1 = generar("lunas")
    X2, y2 = generar("lunas")
    assert np.array_equal(X1, X2) and np.array_equal(y1, y2)


def test_generar_dataset_desconocido():
    with pytest.raises(ValueError):
        generar("espiral")


def test_dividir_es_estratificada_y_sin_solapes():
    X, y = generar("blobs", n=200)
    X_tr, X_te, y_tr, y_te = dividir(X, y, proporcion_test=0.25)
    assert len(X_tr) + len(X_te) == 200
    assert y_te.sum() == 25 and (1 - y_te).sum() == 25
    filas_train = {tuple(f) for f in X_tr}
    assert not any(tuple(f) in filas_train for f in X_te)


def test_dividir_proporcion_invalida():
    X, y = generar("blobs", n=20)
    with pytest.raises(ValueError):
        dividir(X, y, proporcion_test=1.5)


def test_estandarizador():
    X = np.array([[1.0, 5.0], [3.0, 5.0], [5.0, 5.0]])
    Z = Estandarizador().ajustar_transformar(X)
    assert np.allclose(Z.mean(axis=0), 0)
    assert np.allclose(Z[:, 0].std(), 1)
    assert np.allclose(Z[:, 1], 0)  # columna constante: sin división entre 0


def test_estandarizador_sin_ajustar():
    with pytest.raises(RuntimeError):
        Estandarizador().transformar(np.zeros((2, 2)))


# --- Métricas ------------------------------------------------------------

def test_exactitud_y_matriz():
    y = [0, 0, 1, 1]
    p = [0, 1, 1, 1]
    assert exactitud(y, p) == 0.75
    assert matriz_confusion(y, p).tolist() == [[1, 1], [0, 2]]


def test_precision_recall_f1():
    precision, recall, f1 = precision_recall_f1([0, 0, 1, 1], [0, 1, 1, 1])
    assert precision == pytest.approx(2 / 3)
    assert recall == 1.0
    assert f1 == pytest.approx(0.8)


def test_precision_sin_positivos_predichos():
    assert precision_recall_f1([1, 1], [0, 0]) == (0.0, 0.0, 0.0)


def test_entropia_cruzada():
    assert entropia_cruzada_binaria([1, 0], [0.999999, 0.000001]) < 1e-4
    assert entropia_cruzada_binaria([1], [0.5]) == pytest.approx(np.log(2))
    assert np.isfinite(entropia_cruzada_binaria([1], [0.0]))  # recorte con eps


def test_exactitud_errores():
    with pytest.raises(ValueError):
        exactitud([0, 1], [0])
    with pytest.raises(ValueError):
        exactitud([], [])


# --- Modelos lineales ----------------------------------------------------

def test_sigmoide_estable():
    z = np.array([-1000.0, 0.0, 1000.0])
    s = sigmoide(z)
    assert np.all(np.isfinite(s))
    assert s.tolist() == pytest.approx([0.0, 0.5, 1.0])


def test_perceptron_aprende_and():
    X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=float)
    y = np.array([0, 0, 0, 1])
    modelo = Perceptron(tasa=0.1, epocas=100).entrenar(X, y)
    assert modelo.predecir(X).tolist() == y.tolist()
    assert modelo.historial[-1] == 0  # convergió


def test_perceptron_no_puede_con_xor():
    X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=float)
    y = np.array([0, 1, 1, 0])
    modelo = Perceptron(epocas=100).entrenar(X, y)
    assert exactitud(y, modelo.predecir(X)) < 1.0
    assert len(modelo.historial) == 100  # nunca llega a 0 errores


def test_logistica_baja_la_perdida_y_separa_blobs():
    X_tr, X_te, y_tr, y_te = preparar("blobs")
    modelo = RegresionLogistica().entrenar(X_tr, y_tr)
    assert modelo.historial[-1] < modelo.historial[0]
    assert exactitud(y_te, modelo.predecir(X_te)) >= 0.95
    p = modelo.probabilidades(X_te)
    assert np.all((p >= 0) & (p <= 1))


def test_logistica_gradiente_coincide_con_numerico():
    """El gradiente analítico (p - y) coincide con diferencias finitas."""
    rng = np.random.default_rng(0)
    X = rng.normal(size=(20, 2))
    y = (X[:, 0] > 0).astype(int)
    w = np.array([0.3, -0.2])

    def perdida(w_):
        return entropia_cruzada_binaria(y, sigmoide(X @ w_))

    analitico = X.T @ (sigmoide(X @ w) - y) / len(X)
    h = 1e-6
    numerico = np.array([
        (perdida(w + h * e) - perdida(w - h * e)) / (2 * h) for e in np.eye(2)
    ])
    assert np.allclose(analitico, numerico, atol=1e-6)


def test_l2_encoge_los_pesos():
    X_tr, _, y_tr, _ = preparar("blobs")
    sin = RegresionLogistica(l2=0.0).entrenar(X_tr, y_tr)
    con = RegresionLogistica(l2=0.5).entrenar(X_tr, y_tr)
    assert np.linalg.norm(con.w) < np.linalg.norm(sin.w)


def test_modelo_sin_entrenar_y_entradas_invalidas():
    with pytest.raises(RuntimeError):
        Perceptron().predecir(np.zeros((1, 2)))
    with pytest.raises(RuntimeError):
        RegresionLogistica().predecir(np.zeros((1, 2)))
    with pytest.raises(ValueError):
        Perceptron().entrenar(np.zeros((3, 2)), np.array([0, 1, 2]))
    with pytest.raises(ValueError):
        RegresionLogistica().entrenar(np.zeros(3), np.array([0, 1, 0]))


def test_frontera_ascii():
    X_tr, _, y_tr, _ = preparar("blobs")
    modelo = Perceptron().entrenar(X_tr, y_tr)
    texto = frontera_ascii(modelo, ancho=10, alto=4)
    filas = texto.split("\n")
    assert len(filas) == 4 and all(len(f) == 10 for f in filas)
    assert set(texto) <= {"#", ".", "\n"}


# --- CLI -----------------------------------------------------------------

def test_cli_comandos(capsys):
    assert main.main(["datos"]) == 0
    assert main.main(["entrenar", "--modelo", "perceptron", "--dataset", "xor"]) == 0
    assert main.main(["comparar"]) == 0
    salida = capsys.readouterr().out
    assert "Exactitud test" in salida and "lunas" in salida


def test_cli_parametros_invalidos(capsys):
    assert main.main(["entrenar", "--epocas", "0"]) == 1
    assert "Error" in capsys.readouterr().err
