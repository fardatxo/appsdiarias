"""Tests del día 3: validación cruzada, curvas ROC/PR, umbral y explicaciones."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main  # noqa: E402
from spam.datos import cargar_csv, dividir_train_test  # noqa: E402
from spam.evaluacion import (aplicar_umbral, area_bajo_curva, auc_roc,  # noqa: E402
                             buscar_hiperparametro, curva_precision_recall, curva_roc,
                             elegir_umbral, pliegues_estratificados, precision_media,
                             validacion_cruzada)
from spam.experimentos import entrenar  # noqa: E402
from spam.explicacion import explicar, formatear_explicacion, pesos_lineales  # noqa: E402


@pytest.fixture(scope="module")
def division():
    textos, y = cargar_csv()
    return dividir_train_test(textos, y, semilla=0)


@pytest.fixture(scope="module")
def puntuaciones_aleatorias():
    rng = np.random.default_rng(3)
    y = rng.integers(0, 2, 200)
    # Puntuaciones con señal + ruido y algunos empates (redondeo) para probar casos raros.
    s = np.round(y * 0.8 + rng.normal(0, 0.6, 200), 1)
    return y, s


# --- Pliegues ----------------------------------------------------------------

def test_pliegues_particion_y_estratificados():
    y = np.array([0] * 70 + [1] * 30)
    pliegues = pliegues_estratificados(y, k=5, semilla=1)
    assert len(pliegues) == 5
    validaciones = np.concatenate([va for _, va in pliegues])
    # Cada índice se valida exactamente una vez.
    assert sorted(validaciones) == list(range(100))
    for tr, va in pliegues:
        assert len(np.intersect1d(tr, va)) == 0
        assert len(tr) + len(va) == 100
        assert y[va].sum() == 6  # 30 spam / 5 pliegues


def test_pliegues_errores():
    with pytest.raises(ValueError):
        pliegues_estratificados(np.array([0, 1, 0, 1]), k=1)
    with pytest.raises(ValueError):
        pliegues_estratificados(np.array([0, 0, 0, 0, 1]), k=3)  # solo 1 spam


def test_validacion_cruzada_devuelve_oof(division):
    tx_train, _, y_train, _ = division
    r = validacion_cruzada(tx_train, y_train, "bolsa", "bayes", k=4)
    assert len(r["por_pliegue"]) == 4
    assert r["proba_oof"].shape == (len(tx_train),)
    assert np.all((r["proba_oof"] >= 0) & (r["proba_oof"] <= 1))
    assert 0.9 < r["media"]["f1"] <= 1.0
    assert r["desviacion"]["f1"] >= 0


def test_busqueda_hiperparametro_elige_un_valor_probado(division):
    tx_train, _, y_train, _ = division
    filas, mejor = buscar_hiperparametro(tx_train, y_train, "bolsa", "bayes",
                                         valores=[0.1, 1.0], k=3)
    assert [f["valor"] for f in filas] == [0.1, 1.0]
    assert mejor in (0.1, 1.0)
    assert max(f["media"]["f1"] for f in filas) == pytest.approx(
        next(f["media"]["f1"] for f in filas if f["valor"] == mejor))


# --- Curvas, comparadas con scikit-learn --------------------------------------

def test_auc_y_ap_como_sklearn(puntuaciones_aleatorias):
    from sklearn.metrics import average_precision_score, roc_auc_score

    y, s = puntuaciones_aleatorias
    assert auc_roc(y, s) == pytest.approx(roc_auc_score(y, s), abs=1e-12)
    assert precision_media(y, s) == pytest.approx(average_precision_score(y, s), abs=1e-12)


def test_curva_roc_como_sklearn(puntuaciones_aleatorias):
    from sklearn.metrics import roc_curve

    y, s = puntuaciones_aleatorias
    tfp, tvp, _ = curva_roc(y, s)
    sk_fpr, sk_tpr, _ = roc_curve(y, s, drop_intermediate=False)
    np.testing.assert_allclose(tfp, sk_fpr)
    np.testing.assert_allclose(tvp, sk_tpr)


def test_casos_extremos_auc():
    y = np.array([0, 0, 1, 1])
    assert auc_roc(y, [0.1, 0.2, 0.8, 0.9]) == 1.0     # orden perfecto
    assert auc_roc(y, [0.9, 0.8, 0.2, 0.1]) == 0.0     # orden al revés
    assert auc_roc(y, [0.5, 0.5, 0.5, 0.5]) == 0.5     # todo empatado = azar
    assert area_bajo_curva([0, 1], [1, 1]) == 1.0
    with pytest.raises(ValueError):
        auc_roc([1, 1, 1], [0.1, 0.2, 0.3])


def test_curva_pr_monotonia_del_recall(puntuaciones_aleatorias):
    y, s = puntuaciones_aleatorias
    precision, recall, umbrales = curva_precision_recall(y, s)
    assert np.all(np.diff(recall) >= 0)          # bajar el umbral nunca quita recall
    assert np.all(np.diff(umbrales) < 0)         # umbrales de mayor a menor
    assert recall[-1] == 1.0
    assert np.all((precision > 0) & (precision <= 1))


# --- Umbral ------------------------------------------------------------------

def test_elegir_umbral_max_f1():
    y = np.array([0, 0, 0, 1, 1, 1])
    p = np.array([0.1, 0.2, 0.6, 0.4, 0.8, 0.9])
    umbral, info = elegir_umbral(y, p)
    pred = aplicar_umbral(p, umbral)
    # Con el umbral elegido la F1 es la mejor posible entre todos los cortes.
    from spam.metricas import informe
    f1_elegida = informe(y, pred)["f1"]
    assert f1_elegida == pytest.approx(info["f1"])
    assert all(f1_elegida >= informe(y, aplicar_umbral(p, u))["f1"] - 1e-12 for u in p)


def test_elegir_umbral_con_precision_minima():
    y = np.array([0, 0, 0, 1, 1, 1])
    p = np.array([0.1, 0.2, 0.6, 0.4, 0.8, 0.9])
    umbral, info = elegir_umbral(y, p, precision_minima=1.0)
    assert umbral == 0.8               # por encima de 0.6 (el ham que parece spam)
    assert info["precision"] == 1.0
    assert info["recall"] == pytest.approx(2 / 3)
    np.testing.assert_array_equal(aplicar_umbral(p, umbral), [0, 0, 0, 0, 1, 1])


# --- Explicaciones -----------------------------------------------------------

@pytest.mark.parametrize("repr_, modelo", [("bolsa", "bayes"), ("tfidf", "logistica"),
                                           ("tfidf-bigramas", "bayes")])
def test_explicacion_suma_exactamente_la_prediccion(division, repr_, modelo):
    tx_train, tx_test, y_train, _ = division
    vec, mod = entrenar(tx_train, y_train, repr_, modelo)
    for texto in tx_test[:15]:
        exp = explicar(vec, mod, texto)
        suma = exp["constante"] + sum(c for _, c in exp["contribuciones"])
        assert suma == pytest.approx(exp["log_odds"], abs=1e-9)
        p_modelo = mod.predecir_proba(vec.transformar([texto]))[0, 1]
        assert exp["proba"] == pytest.approx(p_modelo, abs=1e-9)


def test_explicacion_caracteres_agrupa_por_palabra(division):
    tx_train, _, y_train, _ = division
    vec, mod = entrenar(tx_train[:300], y_train[:300], "tfidf-caracteres", "logistica")
    texto = "Has ganado un premio gratis, llama ya"
    exp = explicar(vec, mod, texto)
    palabras = {p for p, _ in exp["contribuciones"]}
    assert {"premio", "gratis", "ganado"} <= palabras  # palabras, no trozos tipo "gra"
    suma = exp["constante"] + sum(c for _, c in exp["contribuciones"])
    assert suma == pytest.approx(exp["log_odds"], abs=1e-9)
    assert exp["proba"] == pytest.approx(mod.predecir_proba(vec.transformar([texto]))[0, 1])


def test_explicacion_spam_claro_empuja_hacia_spam(division):
    tx_train, _, y_train, _ = division
    vec, mod = entrenar(tx_train, y_train, "bolsa", "bayes")
    exp = explicar(vec, mod, "ENHORABUENA has ganado un premio, entra en www.premios.com")
    assert exp["proba"] > 0.9
    termino_top, contrib_top = exp["contribuciones"][0]
    assert contrib_top > 0
    texto = formatear_explicacion(exp)
    assert "P(spam)" in texto and "█" in texto


def test_pesos_lineales_tipo_desconocido():
    with pytest.raises(TypeError):
        pesos_lineales(object())


# --- CLI -----------------------------------------------------------------------

def test_cli_explicar(capsys):
    assert main.main(["explicar", "Has ganado 500€, llama al 905123456", "--n", "5"]) == 0
    salida = capsys.readouterr().out
    assert "log-odds" in salida and "SPAM" in salida


def test_cli_validar(capsys):
    assert main.main(["validar", "--k", "3", "--valores", "0.5", "1"]) == 0
    salida = capsys.readouterr().out
    assert "← mejor" in salida and "Resultado en test" in salida


def test_cli_predecir_con_umbral(capsys):
    mensaje = "Has ganado 500€, llama al 905123456"
    assert main.main(["predecir", mensaje]) == 0
    assert "[SPAM]" in capsys.readouterr().out
    assert main.main(["predecir", mensaje, "--umbral", "1.01"]) == 0  # imposible de alcanzar
    assert "[ham ]" in capsys.readouterr().out
