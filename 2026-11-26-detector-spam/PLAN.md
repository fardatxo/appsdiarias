# PLAN — detector-spam

## Descripción

Proyecto de inteligencia artificial: **procesamiento de lenguaje natural (PLN) clásico
desde cero** aplicado a detectar SMS de spam en español. Se construye todo el pipeline
a mano con numpy — preprocesado de texto, bolsa de palabras, TF-IDF, Naive Bayes y
regresión logística — y se compara con scikit-learn para comprobar que las cuentas
están bien. Al final, el mismo pipeline se reutiliza para análisis de sentimiento.

Datos: un corpus de SMS sintéticos en español generado por código con semilla fija
(plantillas + huecos + erratas + un 3 % de etiquetas mal puestas a propósito), así no
hay que descargar nada y los resultados son reproducibles.

Bloque B (jueves-domingo): 4 días, 4 hitos.

## Tecnologías

- Python 3
- numpy (vectorizadores, modelos y métricas a mano)
- scikit-learn (solo para comparar resultados)
- matplotlib (gráficas en PNG)
- pytest (tests)

## Hitos

- [x] **Día 1 (jue 2026-11-26)** — Estructura base y primer clasificador: generador del
  dataset (1200 SMS, `datos/mensajes.csv`), normalización y tokenización (tildes, URLs,
  teléfonos, cantidades de dinero y números como tokens especiales, palabras vacías),
  bolsa de palabras, **Naive Bayes multinomial** con suavizado de Laplace, división
  train/test estratificada, métricas (exactitud, precisión, recall, F1, matriz de
  confusión), CLI `generar` / `datos` / `evaluar` / `predecir`, gráfica de palabras más
  indicativas, 17 tests (incluida la comparación con `MultinomialNB` de scikit-learn)
  y README inicial.
- [x] **Día 2 (vie 2026-11-27)** — Mejores características: **TF-IDF** a mano (tf
  sublineal, idf suavizado, norma L2), n-gramas (bigramas) y n-gramas de caracteres
  (robustos a erratas); **regresión logística** con descenso de gradiente, momento de
  Nesterov, paso automático 1/L y L2 en numpy; comando `comparar` con una tabla de 4
  representaciones × 2 modelos, prueba de robustez con erratas extra y verificación
  contra `TfidfVectorizer` / `LogisticRegression` (`--sklearn`); `evaluar` y `predecir`
  aceptan `--modelo` / `--repr`; gráficas de curva de pérdida y comparación; 21 tests
  nuevos (38 en total, incluido gradiente frente a diferencias finitas).
- [x] **Día 3 (sáb 2026-11-28)** — Evaluar en serio y explicar: `spam/evaluacion.py` con
  pliegues estratificados, validación cruzada k-fold (media ± desviación y probabilidades
  "fuera de pliegue"), búsqueda en rejilla de `alfa`/`C` (comando `validar`, con curva de
  validación en PNG), curvas ROC y precisión-recall, AUC-ROC y precisión media a mano
  (idénticas a scikit-learn), elección del umbral con validación (máx. F1 o precisión
  mínima) y comparación en test (comando `curvas`, PNG con ROC + PR); `spam/explicacion.py`
  con el comando `explicar`, que desglosa los log-odds de forma exacta por término (o por
  palabra en el modelo de caracteres); `predecir --umbral`; 19 tests nuevos (57 en total).
- [ ] **Día 4 (dom 2026-11-29)** — Reutilizar y pulir: guardar/cargar el modelo en JSON,
  segundo caso de uso (análisis de sentimiento de reseñas generadas), demo web mínima
  con `http.server` para probar mensajes, más tests y README final con métricas reales
  y "qué se aprende".
