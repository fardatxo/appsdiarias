# PLAN — red-neuronal-numpy

## Descripción

Proyecto de inteligencia artificial: **redes neuronales desde cero con numpy**, sin
PyTorch ni TensorFlow. Se empieza por una sola neurona (perceptrón y regresión logística),
se ve dónde se queda corta (problemas que no se separan con una recta, como XOR o las
medias lunas) y se construye una **red multicapa (MLP) con backpropagation** escrita a mano,
con su comprobación de gradientes, optimizadores y una demo para jugar con ella.

Datos: datasets 2D generados por código (blobs, lunas, círculos, XOR) y, más adelante,
el dataset `digits` de scikit-learn. Todo con semillas fijas para que sea reproducible.

Bloque B (jueves-domingo): 4 días, 4 hitos.

## Tecnologías

- Python 3
- numpy (modelos, gradientes y métricas a mano)
- scikit-learn (solo para generar datasets y comparar al final)
- matplotlib (gráficas en PNG)
- pytest (tests)

## Hitos

- [x] **Día 1 (jue 2026-11-19)** — Estructura base y una sola neurona: datasets 2D
  reproducibles, división train/test estratificada y estandarización hechas a mano,
  perceptrón de Rosenblatt, regresión logística por descenso de gradiente (con L2),
  métricas (exactitud, matriz de confusión, precisión/recall/F1, entropía cruzada),
  CLI `datos` / `entrenar` / `comparar`, frontera de decisión en ASCII y en PNG,
  curvas de aprendizaje, 25 tests y README inicial.
- [x] **Día 2 (vie 2026-11-20)** — Red multicapa: capas densas, activaciones (ReLU, tanh,
  sigmoide), forward y **backpropagation** a mano, comprobación numérica de gradientes,
  entrenamiento por mini-lotes. Resolver `xor`, `lunas` y `circulos` y comparar con la
  neurona sola (`comparar` con columna MLP).
  *Hecho:* `red/mlp.py` (capas `Densa` y `Activacion`, `MLP` con mini-lotes y L2,
  `comprobar_gradientes`), CLI `entrenar --modelo mlp --ocultas 16,16 --activacion tanh`,
  `comparar` con columna MLP, comando extra `capacidad` (exactitud según nº de neuronas
  ocultas) y `gradientes` (backprop vs. diferencias finitas), 24 tests nuevos (49 en total).
- [x] **Día 3 (sáb 2026-11-21)** — Entrenar mejor: optimizadores (SGD, momentum, Adam),
  inicialización He/Xavier, regularización L2, conjunto de validación y parada temprana.
  Softmax multiclase y prueba con el dataset `digits` (8×8). Gráficas comparando
  optimizadores.
  *Hecho:* `red/optimizadores.py` (SGD, Momentum, Adam con corrección de sesgo),
  inicializaciones `lecun`/`xavier`/`he`/`pequena`, validación interna estratificada con
  parada temprana que restaura los pesos de la mejor época, salida softmax + entropía
  cruzada categórica (detección automática de multiclase), métricas multiclase.
  Comandos nuevos `optimizadores`, `inicializacion` y `digitos` (97.11 % en test) y
  opciones `--optimizador --init --validacion --paciencia` en `entrenar`. 25 tests nuevos
  (74 en total).
- [x] **Día 4 (dom 2026-11-22)** — Demo y cierre: guardar/cargar el modelo (`.npz`),
  comando para predecir puntos o dígitos, comparación con `MLPClassifier` de scikit-learn,
  pulido, más tests y README final con métricas reales y "qué se aprende".
  *Hecho:* `red/persistencia.py` (receta JSON + pesos + estandarización en `.npz`,
  carga con `allow_pickle=False` y validación de formas), `--guardar` en `entrenar` y
  `digitos`, comando `predecir` (puntos 2D en coordenadas originales, imagen de test por
  índice o dígito dibujado en texto, con ejemplos en `ejemplos/`), comando `sklearn`
  (numpy vs. `MLPClassifier`: 97.11 % frente a 97.78 % en dígitos), gráfica de pesos de
  la capa oculta, 28 tests nuevos (102 en total) y README final.

## Ideas extra

- [ ] Animación (serie de PNG) de cómo cambia la frontera durante el entrenamiento.
- [x] Visualizar qué aprende cada neurona de la capa oculta (día 4, `digitos_pesos.png`).
