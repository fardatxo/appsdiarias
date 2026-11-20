"""Tests del día 2: red multicapa (MLP) y backpropagation."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main  # noqa: E402
from red.datos import preparar  # noqa: E402
from red.metricas import exactitud  # noqa: E402
from red.mlp import ACTIVACIONES, MLP, Activacion, Densa, comprobar_gradientes  # noqa: E402


# --- Piezas sueltas --------------------------------------------------------

@pytest.mark.parametrize("nombre", list(ACTIVACIONES))
def test_derivada_activacion_numerica(nombre):
    f, df = ACTIVACIONES[nombre]
    z = np.array([-2.0, -0.5, 0.3, 1.7])  # evitamos z = 0 (pico de ReLU)
    eps = 1e-6
    numerica = (f(z + eps) - f(z - eps)) / (2 * eps)
    assert np.allclose(df(z), numerica, atol=1e-6)


def test_densa_formas():
    capa = Densa(3, 5, np.random.default_rng(0))
    salida = capa.forward(np.ones((4, 3)))
    assert salida.shape == (4, 5)
    grad_entrada = capa.backward(np.ones((4, 5)))
    assert grad_entrada.shape == (4, 3)
    assert capa.dW.shape == (3, 5) and capa.db.shape == (5,)


def test_activacion_desconocida():
    with pytest.raises(ValueError):
        Activacion("softplus")
    with pytest.raises(ValueError):
        MLP(activacion="softplus")


# --- Backpropagation -------------------------------------------------------

@pytest.mark.parametrize("activacion", list(ACTIVACIONES))
@pytest.mark.parametrize("ocultas", [(), (3,), (4, 3)])
def test_backprop_coincide_con_gradiente_numerico(activacion, ocultas):
    X, _, y, _ = preparar("lunas")
    modelo = MLP(ocultas=ocultas, activacion=activacion, l2=0.05)
    assert comprobar_gradientes(modelo, X[:15], y[:15]) < 1e-6


def test_num_parametros():
    modelo = MLP(ocultas=(4, 3)).construir(2)
    # (2*4+4) + (4*3+3) + (3*1+1) = 12 + 15 + 4
    assert modelo.num_parametros() == 31


# --- Entrenamiento ---------------------------------------------------------

@pytest.mark.parametrize("dataset", ["xor", "circulos", "lunas"])
def test_mlp_resuelve_problemas_no_lineales(dataset):
    X_tr, X_te, y_tr, y_te = preparar(dataset)
    modelo = MLP(ocultas=(16,), epocas=300).entrenar(X_tr, y_tr)
    assert exactitud(y_te, modelo.predecir(X_te)) >= 0.9


def test_perdida_baja_al_entrenar():
    X_tr, _, y_tr, _ = preparar("circulos")
    modelo = MLP(ocultas=(8,), epocas=100).entrenar(X_tr, y_tr)
    assert modelo.historial[-1] < modelo.historial[0] / 2


def test_mlp_es_reproducible():
    X_tr, X_te, y_tr, _ = preparar("xor")
    a = MLP(ocultas=(8,), epocas=50).entrenar(X_tr, y_tr).probabilidades(X_te)
    b = MLP(ocultas=(8,), epocas=50).entrenar(X_tr, y_tr).probabilidades(X_te)
    assert np.array_equal(a, b)


def test_mlp_sin_ocultas_es_lineal():
    # Sin capas ocultas el MLP es una regresión logística: no puede con XOR
    X_tr, X_te, y_tr, y_te = preparar("xor")
    modelo = MLP(ocultas=(), epocas=200).entrenar(X_tr, y_tr)
    assert exactitud(y_te, modelo.predecir(X_te)) < 0.7


def test_mlp_parametros_invalidos():
    with pytest.raises(ValueError):
        MLP(ocultas=(4, 0))
    with pytest.raises(ValueError):
        MLP(tasa=0)
    with pytest.raises(RuntimeError):
        MLP().predecir(np.zeros((1, 2)))
    with pytest.raises(ValueError):
        MLP().entrenar(np.zeros((3, 2)), np.array([0, 1, 5]))


# --- CLI -------------------------------------------------------------------

def test_leer_ocultas():
    assert main.leer_ocultas("16,8") == (16, 8)
    assert main.leer_ocultas("0") == ()
    with pytest.raises(ValueError):
        main.leer_ocultas("a,b")
    with pytest.raises(ValueError):
        main.leer_ocultas("4,-1")


def test_cli_mlp(capsys):
    assert main.main(["entrenar", "--modelo", "mlp", "--dataset", "xor",
                      "--ocultas", "8", "--epocas", "100"]) == 0
    assert main.main(["gradientes"]) == 0
    salida = capsys.readouterr().out
    assert "Arquitectura: 2 -> 8 -> 1" in salida
    assert "Backprop correcto" in salida
    assert main.main(["entrenar", "--modelo", "mlp", "--ocultas", "x"]) == 1
