"""Tests del día 3: optimizadores, inicialización, validación/parada temprana
y clasificación multiclase con softmax."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main  # noqa: E402
from red.datos import preparar, preparar_digitos  # noqa: E402
from red.metricas import (  # noqa: E402
    entropia_cruzada_categorica,
    exactitud,
    matriz_confusion_multiclase,
)
from red.mlp import (  # noqa: E402
    INICIALIZACIONES,
    MLP,
    Densa,
    comprobar_gradientes,
    desviacion_activaciones,
    softmax,
)
from red.optimizadores import SGD, Adam, Momentum, crear_optimizador  # noqa: E402


# --- Optimizadores ----------------------------------------------------------

def test_sgd_un_paso():
    w = np.array([1.0, 2.0])
    SGD(tasa=0.5).paso([(w, np.array([2.0, -2.0]))])
    assert np.allclose(w, [0.0, 3.0])


def test_momentum_acumula_velocidad():
    w = np.array([0.0])
    opt = Momentum(tasa=1.0, beta=0.5)
    g = np.array([1.0])
    opt.paso([(w, g)])   # v = -1        -> w = -1
    opt.paso([(w, g)])   # v = -0.5 - 1  -> w = -2.5
    assert np.allclose(w, [-2.5])


def test_adam_primer_paso_es_la_tasa():
    # Con la corrección de sesgo, el primer paso de Adam mide ~tasa en cada
    # peso, sea cual sea el tamaño del gradiente.
    w = np.array([0.0, 0.0])
    Adam(tasa=0.1).paso([(w, np.array([1000.0, -0.001]))])
    assert np.allclose(w, [-0.1, 0.1], atol=1e-4)


def test_optimizador_invalido():
    with pytest.raises(ValueError):
        crear_optimizador("rmsprop")
    with pytest.raises(ValueError):
        SGD(tasa=-1)
    with pytest.raises(ValueError):
        MLP(optimizador="rmsprop")


@pytest.mark.parametrize("optimizador", ["sgd", "momentum", "adam"])
def test_todos_los_optimizadores_aprenden(optimizador):
    X_tr, X_te, y_tr, y_te = preparar("circulos")
    modelo = MLP(ocultas=(16,), optimizador=optimizador, epocas=100).entrenar(X_tr, y_tr)
    assert modelo.historial[-1] < modelo.historial[0]
    assert exactitud(y_te, modelo.predecir(X_te)) >= 0.9


def test_adam_baja_la_perdida_antes_que_sgd():
    X_tr, _, y_tr, _ = preparar("lunas")
    sgd = MLP(ocultas=(16, 16), optimizador="sgd", epocas=10).entrenar(X_tr, y_tr)
    adam = MLP(ocultas=(16, 16), optimizador="adam", epocas=10).entrenar(X_tr, y_tr)
    assert adam.historial[-1] < sgd.historial[-1]


# --- Inicialización ---------------------------------------------------------

@pytest.mark.parametrize("nombre,esperada", [
    ("lecun", np.sqrt(1 / 200)), ("xavier", np.sqrt(2 / 300)),
    ("he", np.sqrt(2 / 200)), ("pequena", 0.01)])
def test_escala_inicializacion(nombre, esperada):
    capa = Densa(200, 100, np.random.default_rng(0), nombre)
    assert abs(capa.W.std() - esperada) / esperada < 0.05


def test_inicializacion_desconocida():
    with pytest.raises(ValueError):
        MLP(inicializacion="aleatoria")


def test_pesos_pequenos_apagan_la_senal():
    X, _, _, _ = preparar("circulos")
    profunda = (32,) * 6
    mala = MLP(ocultas=profunda, inicializacion="pequena").construir(2)
    buena = MLP(ocultas=profunda, activacion="relu", inicializacion="he").construir(2)
    assert desviacion_activaciones(mala, X)[-1] < 1e-6
    assert desviacion_activaciones(buena, X)[-1] > 0.1
    assert set(INICIALIZACIONES) == {"lecun", "xavier", "he", "pequena"}


# --- Validación y parada temprana -------------------------------------------

def test_validacion_guarda_historial():
    X_tr, _, y_tr, _ = preparar("lunas")
    modelo = MLP(ocultas=(8,), epocas=20, validacion=0.2).entrenar(X_tr, y_tr)
    assert len(modelo.historial_val) == len(modelo.exactitud_val) == 20
    assert 1 <= modelo.mejor_epoca <= 20


def test_parada_temprana_para_y_restaura_la_mejor_epoca():
    X_tr, _, y_tr, _ = preparar("lunas")
    modelo = MLP(ocultas=(64, 64), optimizador="adam", epocas=1000,
                 validacion=0.25, paciencia=10).entrenar(X_tr, y_tr)
    epocas = len(modelo.historial)
    assert epocas < 1000
    assert epocas == modelo.mejor_epoca + 10
    # Los pesos restaurados dan exactamente la mejor pérdida de validación
    from red.datos import dividir
    _, X_val, _, y_val = dividir(X_tr, y_tr, 0.25, modelo.semilla)
    mejor = modelo.historial_val[modelo.mejor_epoca - 1]
    assert np.isclose(modelo.perdida(X_val, y_val.astype(float)), mejor)


def test_parada_temprana_sin_validacion_es_error():
    with pytest.raises(ValueError):
        MLP(paciencia=5)
    with pytest.raises(ValueError):
        MLP(validacion=1.0)


# --- Softmax y multiclase ---------------------------------------------------

def test_softmax_suma_uno_y_es_estable():
    P = softmax(np.array([[1.0, 2.0, 3.0], [1000.0, 1000.0, -1000.0]]))
    assert np.allclose(P.sum(axis=1), 1.0)
    assert np.all(np.isfinite(P))
    assert np.allclose(P[1], [0.5, 0.5, 0.0])


def test_entropia_categorica():
    P = np.array([[0.7, 0.2, 0.1], [0.1, 0.1, 0.8]])
    esperada = -(np.log(0.7) + np.log(0.8)) / 2
    assert np.isclose(entropia_cruzada_categorica([0, 2], P), esperada)


def test_matriz_confusion_multiclase():
    m = matriz_confusion_multiclase([0, 1, 2, 2], [0, 2, 2, 2], 3)
    assert m.tolist() == [[1, 0, 0], [0, 0, 1], [0, 0, 2]]


@pytest.mark.parametrize("activacion", ["tanh", "relu"])
def test_backprop_softmax_coincide_con_numerico(activacion):
    rng = np.random.default_rng(3)
    X = rng.normal(size=(12, 4))
    y = np.arange(12) % 3
    modelo = MLP(ocultas=(5,), activacion=activacion, l2=0.01)
    assert comprobar_gradientes(modelo, X, y) < 1e-6
    assert modelo.n_salidas == 3


def test_etiquetas_multiclase_invalidas():
    X = np.zeros((4, 2))
    with pytest.raises(ValueError):
        MLP().entrenar(X, np.array([0, 1, 3, 3]))   # falta la clase 2
    with pytest.raises(ValueError):
        MLP().entrenar(X, np.array([0.5, 1, 2, 0]))  # no son enteros


def test_mlp_aprende_digitos():
    X_tr, X_te, y_tr, y_te = preparar_digitos()
    assert X_tr.shape[1] == 64 and set(np.unique(y_tr)) == set(range(10))
    modelo = MLP(ocultas=(32,), activacion="relu", optimizador="adam",
                 inicializacion="he", epocas=60, validacion=0.2,
                 paciencia=10).entrenar(X_tr, y_tr)
    P = modelo.probabilidades(X_te)
    assert P.shape == (len(X_te), 10)
    assert np.allclose(P.sum(axis=1), 1.0)
    assert exactitud(y_te, modelo.predecir(X_te)) >= 0.93


# --- CLI ----------------------------------------------------------------------

def test_cli_dia3(capsys):
    assert main.main(["optimizadores", "--epocas", "5"]) == 0
    assert main.main(["inicializacion", "--capas", "3"]) == 0
    assert main.main(["digitos", "--epocas", "15", "--paciencia", "0"]) == 0
    assert main.main(["entrenar", "--modelo", "mlp", "--dataset", "lunas",
                      "--optimizador", "adam", "--validacion", "0.2",
                      "--paciencia", "5", "--epocas", "100"]) == 0
    salida = capsys.readouterr().out
    assert "adam" in salida and "momentum" in salida
    assert "pequena" in salida
    assert "Matriz de confusión" in salida and "Exactitud por dígito" in salida
    assert "pesos restaurados" in salida
    # paciencia sin validación -> error controlado
    assert main.main(["entrenar", "--modelo", "mlp", "--paciencia", "5"]) == 1
