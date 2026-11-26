"""Tests del día 1: preprocesado, dataset, bolsa de palabras, Naive Bayes y métricas."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main  # noqa: E402
from spam.bayes import NaiveBayesMultinomial  # noqa: E402
from spam.datos import cargar_csv, dividir_train_test, generar_mensajes, guardar_csv  # noqa: E402
from spam.metricas import informe, matriz_confusion  # noqa: E402
from spam.texto import TOKEN_DINERO, TOKEN_TELEFONO, TOKEN_URL, quitar_tildes, tokenizar  # noqa: E402
from spam.vectorizador import BolsaDePalabras  # noqa: E402


# --- Texto -----------------------------------------------------------------

def test_quitar_tildes_conserva_enie():
    assert quitar_tildes("Canción de España") == "Cancion de España"


def test_tokenizar_normaliza_y_quita_vacias():
    assert tokenizar("¡GRATIS! El premio es para TI") == ["!", "gratis", "!", "premio"]


def test_tokenizar_tokens_especiales():
    tokens = tokenizar("Gana 500€ en www.premios.com o llama al 612 345 678")
    assert TOKEN_DINERO in tokens and TOKEN_URL in tokens and TOKEN_TELEFONO in tokens
    assert "500" not in tokens


# --- Datos -----------------------------------------------------------------

def test_generador_reproducible_y_sin_duplicados():
    a = generar_mensajes(n=200, semilla=7)
    b = generar_mensajes(n=200, semilla=7)
    assert a == b
    assert len({t for t, _ in a}) == len(a) == 200
    assert {e for _, e in a} == {"ham", "spam"}


def test_csv_ida_y_vuelta(tmp_path):
    mensajes = [("hola", "ham"), ("premio gratis", "spam")]
    ruta = tmp_path / "m.csv"
    guardar_csv(mensajes, ruta)
    textos, y = cargar_csv(ruta)
    assert textos == ["hola", "premio gratis"] and list(y) == [0, 1]


def test_cargar_csv_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError):
        cargar_csv(tmp_path / "no.csv")


def test_division_estratificada():
    textos = [f"m{i}" for i in range(100)]
    y = np.array([1] * 20 + [0] * 80)
    tr, te, ytr, yte = dividir_train_test(textos, y, prop_test=0.25)
    assert len(tr) == 75 and len(te) == 25
    assert yte.sum() == 5 and ytr.sum() == 15
    assert set(tr).isdisjoint(te)


# --- Bolsa de palabras -----------------------------------------------------

def test_bolsa_de_palabras_recuentos():
    vec = BolsaDePalabras()
    X = vec.ajustar_transformar(["gratis gratis premio", "hola amigo"])
    assert vec.palabras == ["amigo", "gratis", "hola", "premio"]
    assert X.tolist() == [[0, 2, 0, 1], [1, 0, 1, 0]]
    # Palabras no vistas en el ajuste se ignoran.
    assert vec.transformar(["palabra nueva gratis"]).tolist() == [[0, 1, 0, 0]]


def test_bolsa_min_frecuencia():
    vec = BolsaDePalabras(min_frecuencia=2).ajustar(["gratis premio", "gratis hola"])
    assert vec.palabras == ["gratis"]


def test_transformar_sin_ajustar_falla():
    with pytest.raises(RuntimeError):
        BolsaDePalabras().transformar(["hola"])


# --- Naive Bayes -----------------------------------------------------------

def test_naive_bayes_ejemplo_a_mano():
    # 2 palabras, clase 0 usa sobre todo la palabra 0 y clase 1 la palabra 1.
    X = np.array([[3, 0], [2, 1], [0, 4]])
    y = np.array([0, 0, 1])
    nb = NaiveBayesMultinomial(alfa=1.0).entrenar(X, y)
    # P(w | clase 0) = (5+1, 1+1) / 8 ; P(w | clase 1) = (0+1, 4+1) / 6
    assert np.allclose(np.exp(nb.log_verosimilitud_[0]), [6 / 8, 2 / 8])
    assert np.allclose(np.exp(nb.log_verosimilitud_[1]), [1 / 6, 5 / 6])
    assert np.allclose(np.exp(nb.log_prior_), [2 / 3, 1 / 3])
    assert nb.predecir(np.array([[1, 0], [0, 3]])).tolist() == [0, 1]
    assert np.allclose(nb.predecir_proba(X).sum(axis=1), 1)


def test_naive_bayes_igual_que_sklearn():
    from sklearn.naive_bayes import MultinomialNB

    rng = np.random.default_rng(0)
    X = rng.integers(0, 5, size=(60, 12))
    y = rng.integers(0, 2, size=60)
    nuestro = NaiveBayesMultinomial(alfa=0.5).entrenar(X, y)
    sk = MultinomialNB(alpha=0.5).fit(X, y)
    assert np.allclose(nuestro.predecir_proba(X), sk.predict_proba(X))
    assert (nuestro.predecir(X) == sk.predict(X)).all()


def test_naive_bayes_errores():
    with pytest.raises(ValueError):
        NaiveBayesMultinomial(alfa=-1)
    with pytest.raises(RuntimeError):
        NaiveBayesMultinomial().predecir(np.zeros((1, 2)))
    with pytest.raises(ValueError):
        NaiveBayesMultinomial().entrenar(np.array([[-1, 0]]), np.array([0]))


# --- Métricas --------------------------------------------------------------

def test_metricas():
    y_real = [0, 0, 0, 1, 1, 1, 1]
    y_pred = [0, 0, 1, 1, 1, 0, 1]
    assert matriz_confusion(y_real, y_pred).tolist() == [[2, 1], [1, 3]]
    inf = informe(y_real, y_pred)
    assert inf["precision"] == pytest.approx(3 / 4)
    assert inf["recall"] == pytest.approx(3 / 4)
    assert inf["exactitud"] == pytest.approx(5 / 7)
    assert informe([0, 0], [0, 0])["f1"] == 0.0  # sin positivos: no divide entre 0


# --- Extremo a extremo -----------------------------------------------------

def test_pipeline_completo_supera_90():
    mensajes = generar_mensajes(n=800, semilla=3)
    textos = [t for t, _ in mensajes]
    y = np.array([1 if e == "spam" else 0 for _, e in mensajes])
    tr, te, ytr, yte = dividir_train_test(textos, y)
    vec, modelo = main.entrenar_modelo(tr, ytr)
    assert informe(yte, modelo.predecir(vec.transformar(te)))["exactitud"] > 0.9


def test_cli_generar_y_predecir(tmp_path, capsys):
    ruta = str(tmp_path / "m.csv")
    assert main.main(["--csv", ruta, "generar", "--n", "300"]) == 0
    assert main.main(["--csv", ruta, "predecir", "ENHORABUENA has ganado un premio GRATIS"]) == 0
    assert "[SPAM]" in capsys.readouterr().out


def test_cli_sin_dataset(tmp_path):
    assert main.main(["--csv", str(tmp_path / "no.csv"), "evaluar"]) == 1
