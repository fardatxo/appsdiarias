"""Tests del día 4: guardar/cargar modelos, predecir con ellos, dígitos
dibujados en texto y comandos nuevos de la CLI."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main  # noqa: E402
from red.datos import (  # noqa: E402
    TINTA,
    Estandarizador,
    dibujo_ascii,
    dividir_digitos_crudos,
    leer_dibujo,
    preparar,
    preparar_digitos,
)
from red.mlp import MLP  # noqa: E402
from red.persistencia import cargar_modelo, guardar_modelo  # noqa: E402

EJEMPLOS = Path(__file__).resolve().parent.parent / "ejemplos"


@pytest.fixture(scope="module")
def modelo_lunas():
    X_train, X_test, y_train, y_test, escala = preparar("lunas", con_escala=True)
    modelo = MLP(ocultas=(8,), epocas=60, optimizador="adam").entrenar(X_train, y_train)
    return modelo, escala, X_test


@pytest.fixture(scope="module")
def modelo_digitos():
    X_train, X_test, y_train, y_test, escala = preparar_digitos(con_escala=True)
    modelo = MLP(ocultas=(32,), activacion="relu", optimizador="adam",
                 inicializacion="he", epocas=40).entrenar(X_train, y_train)
    return modelo, escala, X_test, y_test


# --- Guardar y cargar ---------------------------------------------------------

def test_guardar_y_cargar_da_las_mismas_predicciones(tmp_path, modelo_lunas):
    modelo, escala, X_test = modelo_lunas
    ruta = guardar_modelo(modelo, tmp_path / "m.npz", escala, info={"dataset": "lunas"})
    cargado, escala2, info = cargar_modelo(ruta)
    assert np.allclose(cargado.probabilidades(X_test), modelo.probabilidades(X_test))
    assert np.allclose(escala2.media, escala.media)
    assert np.allclose(escala2.desviacion, escala.desviacion)
    assert info == {"dataset": "lunas"}
    assert cargado.ocultas == modelo.ocultas
    assert cargado.optimizador == "adam"


def test_guardar_multiclase(tmp_path, modelo_digitos):
    modelo, escala, X_test, _ = modelo_digitos
    cargado, _, _ = cargar_modelo(guardar_modelo(modelo, tmp_path / "d", escala))
    assert cargado.multiclase and cargado.n_salidas == 10
    assert np.array_equal(cargado.predecir(X_test), modelo.predecir(X_test))


def test_guardar_anade_extension(tmp_path, modelo_lunas):
    ruta = guardar_modelo(modelo_lunas[0], tmp_path / "sin_extension")
    assert ruta.suffix == ".npz" and ruta.exists()


def test_cargar_sin_escala(tmp_path, modelo_lunas):
    _, escala, _ = cargar_modelo(guardar_modelo(modelo_lunas[0], tmp_path / "m.npz"))
    assert escala is None


def test_no_se_guarda_modelo_sin_entrenar(tmp_path):
    with pytest.raises(RuntimeError):
        guardar_modelo(MLP(), tmp_path / "m.npz")


def test_no_se_guarda_estandarizador_sin_ajustar(tmp_path, modelo_lunas):
    with pytest.raises(ValueError):
        guardar_modelo(modelo_lunas[0], tmp_path / "m.npz", Estandarizador())


def test_cargar_fichero_inexistente(tmp_path):
    with pytest.raises(ValueError, match="No existe"):
        cargar_modelo(tmp_path / "nada.npz")


def test_cargar_fichero_que_no_es_modelo(tmp_path):
    basura = tmp_path / "basura.npz"
    basura.write_text("esto no es un npz")
    with pytest.raises(ValueError):
        cargar_modelo(basura)
    otro = tmp_path / "otro.npz"
    np.savez(otro, x=np.zeros(3))
    with pytest.raises(ValueError, match="no es un modelo"):
        cargar_modelo(otro)


def test_cargar_pesos_que_no_cuadran(tmp_path, modelo_lunas):
    ruta = guardar_modelo(modelo_lunas[0], tmp_path / "m.npz")
    with np.load(ruta) as datos:
        contenido = dict(datos)
    contenido["W0"] = np.zeros((3, 3))
    np.savez(ruta, **contenido)
    with pytest.raises(ValueError, match="no cuadran"):
        cargar_modelo(ruta)


# --- Dígitos dibujados en texto --------------------------------------------

def test_leer_dibujo_intensidades():
    texto = "@" * 8 + "\n" + "\n".join([" " * 8] * 7)
    pixeles = leer_dibujo(texto)
    assert pixeles.shape == (64,)
    assert np.all(pixeles[:8] == 16) and np.all(pixeles[8:] == 0)


def test_leer_dibujo_rellena_lineas_cortas_e_ignora_bordes():
    texto = "\n\n" + "\n".join(["#"] * 8) + "\n\n"
    pixeles = leer_dibujo(texto).reshape(8, 8)
    assert np.all(pixeles[:, 0] > 0) and np.all(pixeles[:, 1:] == 0)


@pytest.mark.parametrize("texto", ["#\n#", "\n".join(["#########"] * 8)])
def test_leer_dibujo_tamano_incorrecto(texto):
    with pytest.raises(ValueError):
        leer_dibujo(texto)


def test_dibujo_ascii_ida_y_vuelta():
    pixeles = np.array([round(i * 16 / (len(TINTA) - 1)) for i in range(len(TINTA))]
                       * 7)[:64].astype(float)
    assert np.allclose(leer_dibujo(dibujo_ascii(pixeles)), pixeles)


def test_division_cruda_coincide_con_la_estandarizada():
    _, X_test_crudo, _, y_test_crudo = dividir_digitos_crudos()
    _, X_test, _, y_test, escala = preparar_digitos(con_escala=True)
    assert np.array_equal(y_test, y_test_crudo)
    assert np.allclose(escala.transformar(X_test_crudo), X_test)


@pytest.mark.parametrize("nombre, digito", [("siete", 7), ("uno", 1), ("cero", 0)])
def test_ejemplos_dibujados_se_reconocen(modelo_digitos, nombre, digito):
    modelo, escala, _, _ = modelo_digitos
    pixeles = leer_dibujo((EJEMPLOS / f"{nombre}.txt").read_text(encoding="utf-8"))
    assert modelo.predecir(escala.transformar(pixeles[None, :]))[0] == digito


# --- CLI --------------------------------------------------------------------

def test_cli_entrenar_guardar_y_predecir_puntos(tmp_path, capsys):
    ruta = tmp_path / "lunas.npz"
    assert main.main(["entrenar", "--modelo", "mlp", "--dataset", "lunas",
                      "--epocas", "50", "--optimizador", "adam",
                      "--guardar", str(ruta)]) == 0
    assert ruta.exists()
    capsys.readouterr()
    assert main.main(["predecir", "--modelo", str(ruta),
                      "--punto", "0,1", "--punto", "1,-0.5"]) == 0
    salida = capsys.readouterr().out
    # (0, 1) está en la luna de arriba (clase 0); (1, -0.5) en la de abajo (clase 1)
    assert "(+0.00, +1.00) -> clase 0" in salida
    assert "(+1.00, -0.50) -> clase 1" in salida


def test_cli_predecir_sin_punto_muestra_frontera(tmp_path, capsys, modelo_lunas):
    modelo, escala, _ = modelo_lunas
    ruta = guardar_modelo(modelo, tmp_path / "m.npz", escala)
    assert main.main(["predecir", "--modelo", str(ruta)]) == 0
    assert "#" in capsys.readouterr().out


def test_cli_predecir_digito(tmp_path, capsys, modelo_digitos):
    modelo, escala, _, _ = modelo_digitos
    ruta = guardar_modelo(modelo, tmp_path / "d.npz", escala)
    assert main.main(["predecir", "--modelo", str(ruta), "--indice", "3"]) == 0
    salida = capsys.readouterr().out
    assert "Dígito real: 5" in salida and "Predicción:" in salida
    assert main.main(["predecir", "--modelo", str(ruta),
                      "--dibujo", str(EJEMPLOS / "siete.txt")]) == 0
    assert "Predicción: 7" in capsys.readouterr().out


@pytest.mark.parametrize("extra", [["--punto", "1,2"], ["--indice", "9999"],
                                   ["--dibujo", "no_existe.txt"]])
def test_cli_predecir_digito_errores(tmp_path, capsys, modelo_digitos, extra):
    modelo, escala, _, _ = modelo_digitos
    ruta = guardar_modelo(modelo, tmp_path / "d.npz", escala)
    assert main.main(["predecir", "--modelo", str(ruta), *extra]) == 1
    assert "Error" in capsys.readouterr().err


def test_cli_predecir_punto_mal_escrito(tmp_path, capsys, modelo_lunas):
    ruta = guardar_modelo(modelo_lunas[0], tmp_path / "m.npz", modelo_lunas[1])
    assert main.main(["predecir", "--modelo", str(ruta), "--punto", "1;2"]) == 1
    assert main.main(["predecir", "--modelo", str(ruta), "--indice", "0"]) == 1


def test_cli_guardar_solo_mlp(tmp_path, capsys):
    assert main.main(["entrenar", "--modelo", "logistica",
                      "--guardar", str(tmp_path / "x.npz")]) == 1


def test_cli_sklearn(capsys):
    assert main.main(["sklearn", "--epocas", "20"]) == 0
    salida = capsys.readouterr().out
    assert "digitos" in salida and "sklearn" in salida


def test_grafica_pesos_digitos(tmp_path, modelo_digitos):
    from red.visual import grafica_pesos_digitos
    ruta = grafica_pesos_digitos(modelo_digitos[0].densas()[0].W, tmp_path / "p.png")
    assert ruta.exists() and ruta.stat().st_size > 0
