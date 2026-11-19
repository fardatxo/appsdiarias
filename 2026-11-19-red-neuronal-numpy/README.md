# red-neuronal-numpy 🚧

Redes neuronales **desde cero con numpy**: del perceptrón de una sola neurona a una red
multicapa con backpropagation, sin PyTorch ni TensorFlow, para entender qué pasa por dentro.

> Proyecto en curso (bloque de IA, 19-22 nov 2026). Ver [PLAN.md](PLAN.md).

## Estado actual (día 1/4)

De momento hay **modelos de una sola neurona**:

- **Perceptrón** (Rosenblatt): calcula `z = x·w + b` y predice 1 si `z ≥ 0`. Solo aprende
  cuando se equivoca: mueve la recta hacia el ejemplo mal clasificado.
- **Regresión logística**: la misma neurona, pero con activación **sigmoide**
  `σ(z) = 1/(1+e^-z)`, que da una probabilidad. Se entrena con **descenso de gradiente**
  minimizando la **entropía cruzada**; su gradiente sale sorprendentemente simple: `(p − y)·x`.
  Opcionalmente con regularización **L2** (penaliza pesos grandes).

Y cuatro datasets 2D generados por código: `blobs` (separable con una recta), `lunas`,
`circulos` y `xor` (no separables con una recta).

## Cómo ejecutarlo

```bash
cd 2026-11-19-red-neuronal-numpy
pip install -r requirements.txt

python main.py datos                                   # lista de datasets
python main.py entrenar --modelo perceptron --dataset blobs
python main.py entrenar --modelo logistica --dataset lunas --graficas
python main.py comparar                                # tabla modelo × dataset
python -m pytest -q                                    # tests
```

`entrenar` muestra exactitud en train/test, precisión, recall, F1, la matriz de confusión
y la **frontera de decisión dibujada en ASCII**. Con `--graficas` guarda en `graficas/` la
frontera y la curva de aprendizaje como PNG.

## Resultados reales (día 1)

Exactitud en test (100 ejemplos por dataset, ruido 0.2, semilla 42):

| dataset  | perceptrón | regresión logística |
|----------|-----------:|--------------------:|
| blobs    | 98.00 %    | 99.00 %             |
| lunas    | 76.00 %    | 87.00 %             |
| circulos | 53.00 %    | 42.00 %             |
| xor      | 48.00 %    | 46.00 %             |

**Qué significa:** una neurona sola solo puede trazar una **recta** (frontera lineal).
En `blobs` es suficiente. En `lunas` la recta acierta bastante pero no puede curvarse, y
en `circulos` y `xor` el resultado es como tirar una moneda (~50 %): no existe ninguna
recta que los separe. Es exactamente la limitación que Minsky y Papert señalaron en 1969,
y la razón de ser de las **capas ocultas** que llegan mañana.

![Regresión logística en lunas](graficas/frontera_logistica_lunas.png)

## Métricas usadas

- **Exactitud**: % de aciertos.
- **Precisión**: de los que el modelo dice "clase 1", cuántos lo son.
- **Recall**: de los que son "clase 1", cuántos encuentra.
- **F1**: media armónica de precisión y recall.
- **Entropía cruzada (log-loss)**: la pérdida que se minimiza; castiga mucho estar
  muy seguro y equivocarse.

## Estructura

```
main.py            CLI (datos, entrenar, comparar)
red/datos.py       datasets 2D, división estratificada, estandarización
red/lineales.py    perceptrón, regresión logística, sigmoide estable
red/metricas.py    exactitud, matriz de confusión, precisión/recall/F1, log-loss
red/visual.py      frontera de decisión (PNG y ASCII), curvas de aprendizaje
tests/             tests con pytest (incluye comprobación numérica del gradiente)
graficas/          PNG generados
```
