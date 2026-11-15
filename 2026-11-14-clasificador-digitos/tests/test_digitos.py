"""Tests del clasificador de dígitos. Ejecutar con: python -m pytest"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from digitos.datos import cargar_digitos, dividir_train_test, normalizar, preparar_datos
from digitos.knn import ClasificadorKNN, distancias_euclideas
from digitos.comparar import comparar_modelos
from digitos.dibujo import leer_dibujo, pixeles_a_texto, texto_a_pixeles
from digitos.metricas import (
    exactitud,
    f1_macro,
    formatear_informe,
    formatear_matriz,
    informe_por_clase,
    matriz_confusion,
)
from digitos.validacion import elegir_k, pliegues_estratificados, validacion_cruzada_knn
from digitos.visual import (
    barra,
    digito_ascii,
    grafica_comparacion,
    grafica_errores,
    grafica_exactitud_por_k,
    grafica_matriz_confusion,
)
import main as cli

EJEMPLOS = Path(__file__).resolve().parent.parent / "ejemplos"


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


# ---------- k-NN ponderado ----------

def test_knn_ponderado_gana_el_vecino_cercano():
    # un 0 pegado al punto y dos 1 lejos: por mayoría gana el 1, ponderado el 0
    X, y = [[0.0], [5.0], [6.0]], [0, 1, 1]
    assert ClasificadorKNN(k=3).entrenar(X, y).predecir([[0.5]])[0] == 1
    assert ClasificadorKNN(k=3, ponderado=True).entrenar(X, y).predecir([[0.5]])[0] == 0


def test_knn_ponderado_distancia_cero():
    # una imagen idéntica a una de entrenamiento no debe dar división entre 0
    modelo = ClasificadorKNN(k=2, ponderado=True).entrenar([[0.0], [1.0]], [7, 8])
    proba = modelo.predecir_proba([[0.0]])
    assert np.all(np.isfinite(proba)) and np.isclose(proba.sum(), 1)
    assert modelo.predecir([[0.0]])[0] == 7


def test_predecir_proba_suma_uno():
    X_train, X_test, y_train, _ = preparar_datos()
    for ponderado in (False, True):
        modelo = ClasificadorKNN(k=5, ponderado=ponderado).entrenar(X_train, y_train)
        assert np.allclose(modelo.predecir_proba(X_test[:20]).sum(axis=1), 1)


def test_knn_ponderado_igual_que_scikit_learn():
    from sklearn.neighbors import KNeighborsClassifier

    X_train, X_test, y_train, _ = preparar_datos()
    propio = ClasificadorKNN(k=5, ponderado=True).entrenar(X_train, y_train).predecir(X_test)
    referencia = (
        KNeighborsClassifier(n_neighbors=5, weights="distance")
        .fit(X_train, y_train).predict(X_test)
    )
    assert np.mean(propio == referencia) >= 0.995


# ---------- precisión / recall / F1 ----------

def test_informe_por_clase_a_mano():
    # clase 0: 2 aciertos, 1 se va a la clase 1. clase 1: 3 aciertos, 1 se va a la 0
    informe = informe_por_clase([[2, 1], [1, 3]])
    assert np.allclose(informe["precision"], [2 / 3, 3 / 4])
    assert np.allclose(informe["recall"], [2 / 3, 3 / 4])
    assert informe["soporte"].tolist() == [3, 4]
    assert "precisión" in formatear_informe(informe, [0, 1])


def test_informe_clase_nunca_predicha():
    informe = informe_por_clase([[3, 0], [2, 0]])  # nunca se predice la clase 1
    assert informe["precision"][1] == 0 and informe["f1"][1] == 0
    with pytest.raises(ValueError):
        informe_por_clase([[1, 2, 3]])


def test_informe_igual_que_scikit_learn():
    from sklearn.metrics import f1_score, precision_recall_fscore_support

    X_train, X_test, y_train, y_test = preparar_datos()
    pred = ClasificadorKNN(k=3).entrenar(X_train, y_train).predecir(X_test)
    matriz = matriz_confusion(y_test, pred)
    informe = informe_por_clase(matriz)
    p, r, f, s = precision_recall_fscore_support(y_test, pred)
    assert np.allclose(informe["precision"], p) and np.allclose(informe["recall"], r)
    assert np.allclose(informe["f1"], f) and informe["soporte"].tolist() == s.tolist()
    assert np.isclose(f1_macro(matriz), f1_score(y_test, pred, average="macro"))


# ---------- validación cruzada ----------

def test_pliegues_cubren_todo_sin_repetir():
    y = np.repeat([0, 1, 2], [10, 20, 30])
    pliegues = pliegues_estratificados(y, 5)
    juntos = np.concatenate(pliegues)
    assert sorted(juntos) == list(range(60))
    assert all(len(p) == 12 for p in pliegues)
    # estratificados: cada pliegue lleva 2, 4 y 6 ejemplos de cada clase
    assert all(np.bincount(y[p]).tolist() == [2, 4, 6] for p in pliegues)


def test_pliegues_invalidos():
    with pytest.raises(ValueError):
        pliegues_estratificados([0, 1, 0, 1], 1)
    with pytest.raises(ValueError):
        pliegues_estratificados([0, 1], 3)


def test_validacion_cruzada_y_elegir_k():
    X_train, _, y_train, _ = preparar_datos()
    X, y = X_train[:400], y_train[:400]
    notas = validacion_cruzada_knn(X, y, k=3, n_pliegues=4)
    assert notas.shape == (4,) and notas.mean() > 0.9
    # reproducible: misma semilla, mismas notas
    assert np.array_equal(notas, validacion_cruzada_knn(X, y, k=3, n_pliegues=4))
    mejor, medias = elegir_k(X, y, [1, 3, 99], n_pliegues=4)
    assert mejor in (1, 3) and len(medias) == 3
    assert medias[2] < max(medias)  # un k enorme tiene que ser peor


# ---------- comparación de modelos ----------

def test_comparar_modelos():
    X_train, X_test, y_train, y_test = preparar_datos()
    resultados = comparar_modelos(X_train, y_train, X_test, y_test, k=3)
    assert len(resultados) == 5
    exactitudes = [r["exactitud"] for r in resultados]
    assert exactitudes == sorted(exactitudes, reverse=True)
    assert all(r["exactitud"] > 0.9 and r["f1"] > 0.9 for r in resultados)
    propio = next(r for r in resultados if r["nombre"] == "k-NN propio (k=3)")
    assert propio["fallos"] == round((1 - propio["exactitud"]) * len(y_test))


# ---------- dibujos en fichero de texto ----------

def test_texto_a_pixeles():
    pixeles = texto_a_pixeles("#.\n 9\n\n")
    assert pixeles.shape == (64,)
    imagen = pixeles.reshape(8, 8)
    assert imagen[0, 0] == 1 and imagen[0, 1] == 0 and imagen[1, 1] == 1
    assert imagen.sum() == 2  # el resto se rellena con blanco


@pytest.mark.parametrize("texto", [
    "",                    # vacío
    "........\n" * 8,      # sin tinta
    "#########",           # línea demasiado larga
    "#\n" * 9,             # demasiadas líneas
    "#?",                  # carácter desconocido
])
def test_texto_a_pixeles_errores(texto):
    with pytest.raises(ValueError):
        texto_a_pixeles(texto)


def test_dibujo_ida_y_vuelta():
    _, X_test, _, _ = preparar_datos()
    recuperado = texto_a_pixeles(pixeles_a_texto(X_test[0]))
    # la trama solo tiene 10 niveles de gris y el "." se lee como blanco:
    # se pierde como mucho nivel y medio (los píxeles casi blancos)
    assert np.abs(recuperado - X_test[0]).max() <= 1.5 / 9 + 1e-9


@pytest.mark.parametrize("fichero, esperado", [
    ("cero.txt", 0), ("uno.txt", 1), ("tres.txt", 3), ("seis.txt", 6), ("siete.txt", 7),
])
def test_ejemplos_dibujados(fichero, esperado):
    X_train, _, y_train, _ = preparar_datos()
    modelo = ClasificadorKNN(k=3).entrenar(X_train, y_train)
    assert modelo.predecir(leer_dibujo(EJEMPLOS / fichero))[0] == esperado


def test_leer_dibujo_inexistente(tmp_path):
    with pytest.raises(ValueError):
        leer_dibujo(tmp_path / "no_existe.txt")


# ---------- gráficas ----------

def test_graficas_se_guardan(tmp_path):
    matriz = np.array([[5, 1], [0, 4]])
    rutas = [
        grafica_exactitud_por_k([1, 3], [0.9, 0.95], tmp_path / "k.png", [0.88, 0.93]),
        grafica_matriz_confusion(matriz, [0, 1], tmp_path / "m.png"),
        grafica_errores(np.zeros((3, 64)), [1, 2, 3], [3, 2, 1], tmp_path / "e.png"),
        grafica_comparacion(
            [{"nombre": "k-NN propio", "exactitud": 0.99}, {"nombre": "otro", "exactitud": 0.95}],
            tmp_path / "c.png",
        ),
    ]
    for ruta in rutas:
        assert ruta.stat().st_size > 1000
        assert ruta.read_bytes().startswith(b"\x89PNG")
    with pytest.raises(ValueError):
        grafica_errores(np.zeros((0, 64)), [], [], tmp_path / "vacio.png")


# ---------- CLI (comandos del día 2) ----------

@pytest.fixture
def graficas_temporales(tmp_path, monkeypatch):
    """Hace que la CLI guarde las gráficas en una carpeta temporal."""
    monkeypatch.setattr(cli, "RAIZ", tmp_path)
    monkeypatch.setattr(cli, "CARPETA_GRAFICAS", tmp_path / "graficas")
    return tmp_path / "graficas"


def test_cli_informe(capsys, graficas_temporales):
    cli.main(["informe", "--k", "3"])
    salida = capsys.readouterr().out
    assert "recall" in salida and "Errores: 4 de 450" in salida
    assert (graficas_temporales / "matriz_confusion.png").exists()
    assert (graficas_temporales / "errores.png").exists()


def test_cli_buscar_k(capsys, graficas_temporales):
    cli.main(["buscar-k", "--max-k", "3", "--pliegues", "3"])
    assert "k elegido por validación cruzada" in capsys.readouterr().out
    assert (graficas_temporales / "exactitud_por_k.png").exists()


def test_cli_comparar(capsys, graficas_temporales):
    cli.main(["comparar"])
    salida = capsys.readouterr().out
    assert "SVM" in salida and "k-NN propio (k=3)" in salida
    assert (graficas_temporales / "comparacion_modelos.png").exists()


def test_cli_dibujar(capsys):
    cli.main(["dibujar", str(EJEMPLOS / "siete.txt"), "--ponderado"])
    assert "El modelo cree que es un: 7" in capsys.readouterr().out


def test_cli_ver_guardar_y_dibujar(capsys, tmp_path):
    destino = tmp_path / "digito.txt"
    cli.main(["ver", "--indice", "7", "--guardar", str(destino)])
    assert "Dígito real: 5" in capsys.readouterr().out
    cli.main(["dibujar", str(destino)])
    assert "El modelo cree que es un: 5" in capsys.readouterr().out


@pytest.mark.parametrize("argumentos", [
    ["dibujar", "no_existe.txt"],
    ["evaluar", "--k", "0"],
    ["evaluar", "--k", "5000"],
    ["buscar-k", "--pliegues", "1"],
])
def test_cli_errores(argumentos):
    with pytest.raises(SystemExit) as error:
        cli.main(argumentos)
    assert error.value.code != 0
