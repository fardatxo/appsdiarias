# PLAN — tablero-kanban-php

## Descripción

Una **aplicación web tipo Trello** para organizar tareas en tableros Kanban, hecha en
**PHP puro con SQLite**, sin frameworks ni Composer. Cada tablero tiene columnas
(Por hacer, En curso, Hecho…) y en ellas tarjetas que se crean, editan y mueven.

La idea es ver las piezas que normalmente esconde un framework como Laravel: controlador
frontal, router con parámetros, plantillas con escapado, PDO con consultas preparadas,
transacciones, patrón POST/redirect/GET, avisos "flash" en sesión y protección CSRF.

Proyecto del bloque A (lunes a miércoles): 3 hitos, uno por día.

## Tecnologías

- PHP 8.1 o superior (probado con PHP 8.3): `strict_types`, propiedades `readonly`, `match`
- SQLite mediante PDO (`pdo_sqlite`)
- Servidor integrado de PHP (`php -S`) para desarrollo
- HTML + CSS plano (modo claro/oscuro), JavaScript mínimo solo donde aporte
- Tests con un mini runner propio (sin PHPUnit) y prueba en navegador con Playwright

## Hitos

- [x] **Día 1 (lun 2026-11-23)** — Estructura base y primera versión usable: controlador
  frontal, router con `{id}`, `Respuesta`, vistas con layout y escapado, esquema SQLite
  (tableros → columnas → tarjetas con borrado en cascada), crear/listar/borrar tableros
  (con columnas iniciales), ver un tablero y añadir tarjetas, validación con errores por
  campo, avisos flash, CSRF, páginas de error 404/405/419, 11 tests y README inicial.
- [x] **Día 2 (mar 2026-11-24)** — Trabajar con las tarjetas: editar y borrar tarjetas,
  moverlas entre columnas y reordenarlas (botones ← → ↑ ↓ sin JS y arrastrar y soltar con
  JS progresivo), etiquetas de color y fecha límite (resaltando las vencidas), gestionar
  columnas (añadir, renombrar, borrar) y tests de todo ello.
  *Hecho:* repositorio `Columnas` (añadir, renombrar, borrar sin dejar el tablero vacío,
  reordenar ← →, máximo 10), `Tarjetas` con editar/borrar/mover en transacción manteniendo
  posiciones 0..n-1, migración automática de bases del día 1, respuestas JSON para el
  arrastre (`public/app.js`), avisos de error y 23 tests. Probado en Chromium con Playwright.
- [x] **Día 3 (mié 2026-11-25)** — Búsqueda y filtros (texto, etiqueta, vencidas),
  pequeña API JSON de solo lectura (`/api/tableros/{id}`) y exportación del tablero a
  JSON/CSV, estadísticas del tablero, pulido de la interfaz, más tests y README final.
  *Hecho:* `Filtro` (texto sin tildes ni mayúsculas, todas las palabras, etiqueta y estado
  de fecha; el arrastre se desactiva mientras se filtra), `Estadisticas` (progreso, por
  columna y etiqueta, vencidas y próximas fechas) con su página de barras en CSS,
  `Exportador` a JSON y CSV (BOM para Excel, protección contra inyección de fórmulas,
  respeta los filtros), API `GET /api/tableros` y `/api/tableros/{id}` con errores en JSON,
  31 tests y README final. Probado en Chromium con Playwright.
