# PLAN — clasificador-digitos

## Descripción

Proyecto de inteligencia artificial: un **clasificador de dígitos manuscritos** (0-9).
Usa el dataset `digits` incluido en scikit-learn (1797 imágenes de 8×8 píxeles) y recorre
el pipeline completo de un proyecto de IA: datos → entrenamiento → evaluación → demo.

El corazón del proyecto es un clasificador **k-NN (k vecinos más cercanos) implementado
a mano con numpy**, para entender qué hace un modelo por dentro. Después se compara con
modelos ya hechos de scikit-learn.

Proyecto empezado un sábado: el bloque B (jueves-domingo) solo tiene 2 días por delante,
así que el alcance está ajustado a 2 hitos.

## Tecnologías

- Python 3
- numpy (k-NN y métricas a mano)
- scikit-learn (solo el dataset hoy; modelos de comparación en el hito 2)
- matplotlib (gráficas en PNG)
- pytest (tests)

## Hitos

- [x] **Día 1 (sáb 2026-11-14)** — Estructura base y primer modelo que funciona:
  carga del dataset, división train/test estratificada hecha a mano, k-NN desde cero con
  numpy, métricas (exactitud y matriz de confusión), CLI con `evaluar`, `buscar-k`
  (gráfica exactitud vs. k) y `ver` (dígito en ASCII + predicción), tests y README inicial.
- [ ] **Día 2 (dom)** — Comparación y cierre: comparar el k-NN propio con modelos de
  scikit-learn (regresión logística, SVM, bosque aleatorio), precisión/recall por clase,
  matriz de confusión como imagen PNG, galería de los errores del modelo, demo `dibujar`
  (clasifica un dígito 8×8 escrito en un fichero de texto), pulido, más tests y README final.

## Ideas extra (si sobra tiempo)

- k-NN ponderado por distancia (los vecinos cercanos votan más).
- Validación cruzada para elegir `k` sin mirar el conjunto de test.
