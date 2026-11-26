# detector-spam 🚧

Detector de SMS de spam en español construido **desde cero**: preprocesado de texto,
bolsa de palabras y Naive Bayes escritos a mano con numpy. Es el proyecto de IA de la
semana (jueves a domingo); el plan día a día está en [PLAN.md](PLAN.md).

> Estado: **día 1 de 4**. Ya funciona de extremo a extremo: generar datos → entrenar →
> evaluar → clasificar mensajes nuevos.

## Cómo ejecutarlo

```bash
pip install -r requirements.txt

python main.py generar            # crea datos/mensajes.csv (ya viene incluido)
python main.py datos              # resumen del dataset y ejemplos
python main.py evaluar --grafica  # entrena con train, evalúa en test y guarda un PNG
python main.py predecir "ENHORABUENA has ganado 1000€, entra en www.premios.com" \
                        "¿Quedamos mañana en el parque?"
python -m pytest -q               # 17 tests
```

## Cómo funciona

### 1. Datos

`spam/datos.py` genera 1200 SMS (720 ham y 480 spam) a partir de plantillas con huecos
(nombres, sitios, premios, marcas, enlaces, teléfonos…). Para que no sea un problema
de juguete incluye **casos difíciles** (spam que parece una conversación, como el
timo de "hola mamá, este es mi número nuevo", y mensajes normales que hablan de
ofertas o premios), **erratas** aleatorias y un **3 % de etiquetas invertidas**, que
imitan los errores de etiquetado de los datasets reales. Todo con semilla fija.

### 2. Del texto a números

- **Normalizar** (`spam/texto.py`): minúsculas, sin tildes (conservando la ñ), y las
  cosas que cambian mucho pero significan lo mismo se sustituyen por tokens especiales:
  `<url>`, `<tel>`, `<dinero>`, `<num>`. Así "500€" y "20 euros" cuentan como la misma pista.
- **Tokenizar**: separar en palabras, guardar las exclamaciones como `!` y quitar las
  *palabras vacías* (de, la, que, el…), que salen en todos los mensajes y no ayudan.
- **Bolsa de palabras** (`spam/vectorizador.py`): cada mensaje se convierte en un vector
  con el número de veces que aparece cada palabra del vocabulario. El vocabulario se
  aprende **solo con train**, para no hacer trampas con el test.

### 3. Naive Bayes multinomial

`spam/bayes.py` aplica el teorema de Bayes:
P(spam | mensaje) ∝ P(spam) · Π P(palabra | spam)^recuento.
Es *naive* porque supone que las palabras son independientes entre sí (falso, pero
funciona). P(palabra | clase) se calcula contando, con **suavizado de Laplace** (`alfa`)
para que una palabra no vista no deje la probabilidad a 0, y todo se hace con
**logaritmos** para no perder precisión al multiplicar números muy pequeños. Un test
comprueba que da exactamente las mismas probabilidades que `MultinomialNB` de scikit-learn.

## Resultados (día 1)

`python main.py evaluar` — 900 mensajes de train, 300 de test, vocabulario de 804 palabras, `alfa = 1`:

| Conjunto | Exactitud | Precisión | Recall | F1 |
|----------|-----------|-----------|--------|----|
| train    | 0.966     | 0.966     | 0.947  | 0.957 |
| test     | 0.957     | 0.973     | 0.917  | 0.944 |

Matriz de confusión en test: de 180 mensajes normales, 3 acaban marcados como spam
(falsos positivos); de 120 spam, se escapan 10 (falsos negativos).

**Qué significan:** la *precisión* dice cuántos de los mensajes marcados como spam lo
eran de verdad (lo importante para no perder mensajes buenos); el *recall*, cuánto spam
real se caza; F1 resume las dos. Al revisar los errores se ve que varios son justo las
etiquetas invertidas a propósito (p. ej. "Envía GANAR al 6803…" etiquetado como ham):
el modelo acierta y es la etiqueta la que está mal. Ningún modelo puede llegar al 100 %
con datos ruidosos, y eso es normal.

![Palabras más indicativas](graficas/palabras_indicativas.png)

## Estructura

```
main.py               CLI (generar, datos, evaluar, predecir)
spam/texto.py         normalización y tokenización
spam/datos.py         generador del dataset, CSV y división train/test
spam/vectorizador.py  bolsa de palabras
spam/bayes.py         Naive Bayes multinomial
spam/metricas.py      matriz de confusión, precisión, recall, F1
datos/mensajes.csv    dataset generado (≈80 KB)
graficas/             PNG generados
tests/                tests con pytest
```

## Próximos pasos

TF-IDF, n-gramas y regresión logística (día 2); validación cruzada, curvas ROC/PR y
explicación de predicciones (día 3); guardar el modelo, análisis de sentimiento y demo
web (día 4).
