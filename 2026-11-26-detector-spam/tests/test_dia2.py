"""Tests del día 2: n-gramas, TF-IDF, regresión logística y comparación de modelos."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main  # noqa: E402
from spam.datos import cargar_csv, dividir_train_test, meter_erratas  # noqa: E402
from spam.experimentos import comparar, crear, formatear_tabla, verificar_con_sklearn  # noqa: E402
from spam.logistica import RegresionLogistica, sigmoide  # noqa: E402
from spam.vectorizador import (BolsaDePalabras, TfIdf, VectorizadorTfIdf,  # noqa: E402
                               ngramas_caracteres, ngramas_palabras)


@pytest.fixture(scope="module")
def division():
    textos, y = cargar_csv()
    return dividir_train_test(textos, y, semilla=0)


# --- n-gramas --------------------------------------------------------------

def test_ngramas_palabras():
    assert ngramas_palabras(["premio", "gratis", "ya"], 1, 2) == [
        "premio", "gratis", "ya", "premio gratis", "gratis ya"]
    assert ngramas_palabras(["hola"], 2, 2) == []


def test_ngramas_caracteres_marcan_bordes_y_respetan_especiales():
    trozos = ngramas_caracteres("Gratis www.x.com", 3, 3)
    assert trozos[0] == " gr" and "is " in trozos
    assert "<url>" in trozos  # el token especial no se trocea


def test_ngramas_caracteres_robustos_a_erratas():
    # Una errata cambia la palabra entera, pero comparte la mayoría de trozos.
    a, b = set(ngramas_caracteres("gratis", 2, 4)), set(ngramas_caracteres("gratiss", 2, 4))
    assert len(a & b) / len(a) > 0.7


def test_bolsa_con_bigramas():
    # Los bigramas se forman después de quitar palabras vacías ("de").
    vec = BolsaDePalabras(ngramas=(1, 2)).ajustar(["premio gratis", "gratis de verdad"])
    assert "premio gratis" in vec.vocabulario and "gratis verdad" in vec.vocabulario


def test_bolsa_parametros_invalidos():
    with pytest.raises(ValueError):
        BolsaDePalabras(analizador="frase")
    with pytest.raises(ValueError):
        BolsaDePalabras(ngramas=(2, 1))


# --- TF-IDF ----------------------------------------------------------------

def test_tfidf_a_mano():
    # 2 documentos; el término 0 sale en los dos, el 1 solo en el primero.
    recuentos = np.array([[1.0, 1.0], [2.0, 0.0]])
    tfidf = TfIdf(normalizar=False).ajustar(recuentos)
    np.testing.assert_allclose(tfidf.idf_, [1.0, np.log(3 / 2) + 1])
    X = TfIdf().ajustar(recuentos).transformar(recuentos)
    np.testing.assert_allclose(np.linalg.norm(X, axis=1), [1.0, 1.0])  # filas con norma 1


def test_tfidf_fila_vacia_no_da_nan():
    tfidf = TfIdf().ajustar(np.array([[1.0, 0.0]]))
    assert np.all(tfidf.transformar(np.zeros((1, 2))) == 0)


def test_tfidf_sin_ajustar_falla():
    with pytest.raises(RuntimeError):
        TfIdf().transformar(np.ones((1, 2)))


@pytest.mark.parametrize("opciones", [{}, {"ngramas": (1, 2)},
                                      {"analizador": "caracter", "ngramas": (2, 4)}])
def test_tfidf_igual_que_sklearn(division, opciones):
    from sklearn.feature_extraction.text import TfidfVectorizer

    tx_train, tx_test, _, _ = division
    vec = VectorizadorTfIdf(sublineal=True, **opciones).ajustar(tx_train)
    sk = TfidfVectorizer(analyzer=vec.terminos, vocabulary=vec.vocabulario,
                         sublinear_tf=True).fit(tx_train)
    np.testing.assert_allclose(vec.transformar(tx_test), sk.transform(tx_test).toarray(),
                               atol=1e-12)


# --- Regresión logística ---------------------------------------------------

def test_sigmoide_estable():
    z = np.array([-1000.0, 0.0, 1000.0])
    np.testing.assert_allclose(sigmoide(z), [0.0, 0.5, 1.0])


def test_logistica_separa_datos_sencillos():
    rng = np.random.default_rng(0)
    X = np.vstack([rng.normal(-2, 1, (50, 2)), rng.normal(2, 1, (50, 2))])
    y = np.array([0] * 50 + [1] * 50)
    modelo = RegresionLogistica(C=1.0).entrenar(X, y)
    assert (modelo.predecir(X) == y).mean() > 0.95
    assert modelo.historial_[-1] < modelo.historial_[0]  # la pérdida baja
    np.testing.assert_allclose(modelo.predecir_proba(X).sum(axis=1), 1.0)


def test_logistica_gradiente_numerico():
    # El gradiente analítico debe coincidir con el de diferencias finitas.
    rng = np.random.default_rng(1)
    X, y = rng.normal(size=(20, 3)), rng.integers(0, 2, 20).astype(float)
    m = RegresionLogistica(C=0.5)
    w, b = rng.normal(size=3), 0.3
    _, gw, gb = m._perdida_y_gradiente(X, y, w, b)
    h = 1e-6
    for j in range(3):
        e = np.zeros(3)
        e[j] = h
        num = (m._perdida_y_gradiente(X, y, w + e, b)[0]
               - m._perdida_y_gradiente(X, y, w - e, b)[0]) / (2 * h)
        assert gw[j] == pytest.approx(num, abs=1e-6)
    num_b = (m._perdida_y_gradiente(X, y, w, b + h)[0]
             - m._perdida_y_gradiente(X, y, w, b - h)[0]) / (2 * h)
    assert gb == pytest.approx(num_b, abs=1e-6)


def test_logistica_errores():
    with pytest.raises(ValueError):
        RegresionLogistica(C=0)
    with pytest.raises(ValueError):
        RegresionLogistica().entrenar(np.ones((3, 2)), np.array([0, 1, 2]))
    with pytest.raises(RuntimeError):
        RegresionLogistica().predecir(np.ones((1, 2)))


def test_logistica_igual_que_sklearn(division):
    tx_train, tx_test, y_train, _ = division
    r = verificar_con_sklearn(tx_train, y_train, tx_test, C=10.0)
    assert r["tfidf_dif_max"] < 1e-12
    assert r["logistica_proba_dif_max"] < 1e-4
    assert r["logistica_predicciones_iguales"] == 1.0


# --- Comparación y CLI -----------------------------------------------------

def test_crear_valida_nombres():
    with pytest.raises(ValueError):
        crear("word2vec", "bayes")
    with pytest.raises(ValueError):
        crear("tfidf", "svm")


def test_comparar_todas_las_combinaciones(division):
    tx_train, tx_test, y_train, y_test = division
    filas = comparar(tx_train, y_train, tx_test, y_test,
                     tx_test_erratas=meter_erratas(tx_test, 3, semilla=0))
    assert len(filas) == 8
    assert all(f["f1"] > 0.9 for f in filas)
    assert "← mejor F1" in formatear_tabla(filas)


def test_meter_erratas_reproducible():
    textos = ["hola que tal", "premio gratis"]
    assert meter_erratas(textos, 2, semilla=3) == meter_erratas(textos, 2, semilla=3)
    assert meter_erratas(textos, 2, semilla=3) != textos


def test_cli_evaluar_y_predecir_logistica(capsys):
    assert main.main(["evaluar", "--modelo", "logistica", "--repr", "tfidf"]) == 0
    assert "Descenso de gradiente" in capsys.readouterr().out
    assert main.main(["predecir", "--modelo", "logistica", "--repr", "tfidf-bigramas",
                      "Has ganado un premio, entra en www.premios.com"]) == 0
    assert "[SPAM]" in capsys.readouterr().out


def test_cli_comparar(capsys):
    assert main.main(["comparar", "--erratas", "0"]) == 0
    salida = capsys.readouterr().out
    assert "tfidf-caracteres" in salida and "F1 errat." not in salida
