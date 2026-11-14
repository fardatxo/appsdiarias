# clasificador-digitos

> 🚧 Proyecto en curso — día 1 de 2. Ver [PLAN.md](PLAN.md).

Clasificador de **dígitos manuscritos (0-9)** con un modelo **k-NN implementado a mano
con numpy**. Le das una imagen de 8×8 píxeles y te dice qué número es.

## Qué hace el modelo

**k-NN (k vecinos más cercanos)** es probablemente el modelo de IA más fácil de entender:

1. "Entrenar" es simplemente **memorizar** todas las imágenes de ejemplo con su etiqueta.
2. Para clasificar una imagen nueva se calcula su **distancia** a todas las memorizadas
   (cada imagen es un punto con 64 coordenadas, una por píxel; dos imágenes parecidas
   quedan cerca).
3. Se cogen las **k más cercanas** y se hace una **votación**: gana el dígito más repetido.

`k` es un *hiperparámetro*: no lo aprende el modelo, lo elegimos nosotros. Con `k=1`
el modelo se fía de un único vecino (sensible al ruido); con un `k` muy grande opinan
vecinos que ya no se parecen tanto.

## Datos

Dataset `digits` de scikit-learn: 1797 imágenes de 8×8 en escala de grises (no hay que
descargar nada). Se dividen en **75 % entrenamiento (1347)** y **25 % test (450)**, de
forma estratificada y con semilla fija (`42`), así que los resultados son reproducibles.

El conjunto de test son imágenes que el modelo **nunca ha visto**: es la única forma
honesta de medir si ha aprendido a generalizar y no solo a recordar.

## Resultados (reales, obtenidos al ejecutar el código)

| k | Exactitud en test |
|---|-------------------|
| 1 | 99,11 % |
| 3 | 99,11 % (446/450) |
| 5 | **99,33 %** (447/450) |
| 7 | 98,89 % |
| 9 | 99,11 % |
| 11 | 98,89 % |
| 13 | 98,67 % |
| 15 | 98,44 % |

![Exactitud según k](graficas/exactitud_por_k.png)

- **Exactitud (accuracy)**: porcentaje de imágenes de test bien clasificadas.
- **Matriz de confusión**: tabla "dígito real × dígito predicho". La diagonal son los
  aciertos; fuera de ella se ve *qué se confunde con qué*. Con `k=3` los 4 fallos son:
  un 1 tomado por 5, un 5 por 6, un 5 por 9 y un 8 por 1.

> Ojo: las diferencias entre valores de k son de 1-2 imágenes, así que no son
> significativas. Además, elegir `k` mirando el test es hacer un poco de trampa; lo
> correcto es usar validación cruzada (apuntado en el PLAN).

## Cómo ejecutarlo

```bash
pip install -r requirements.txt

python main.py evaluar --k 3      # exactitud y matriz de confusión
python main.py buscar-k           # compara k=1,3,...,15 y guarda la gráfica
python main.py ver --indice 7     # dibuja un dígito de test y lo clasifica

python -m pytest                  # tests
```

Ejemplo de `ver`:

```
    %%##****..
  ::@@@@**--
    @@::
    **--
    --##
      ##--
  ::::##==
    %%@@::

Dígito real: 5  |  Predicción: 5  (✔ acierto)

Votos de los 3 vecinos más cercanos:
  5: ██████████ 100%
Vecinos: 5 (dist. 0.68), 5 (dist. 0.94), 5 (dist. 1.26)
```

## Estructura

```
main.py              CLI (evaluar, buscar-k, ver)
digitos/
  datos.py           carga, normalización y división train/test estratificada
  knn.py             k-NN desde cero (distancias vectorizadas + votación)
  metricas.py        exactitud y matriz de confusión
  visual.py          dígitos en ASCII y gráfica PNG
tests/               tests con pytest (incluye comparación con scikit-learn)
graficas/            gráficas generadas
```

## Próximo paso (día 2)

Comparar el k-NN propio con modelos de scikit-learn, precisión/recall por clase, matriz
de confusión como imagen, galería de errores y demo para clasificar un dígito dibujado
en un fichero de texto.
