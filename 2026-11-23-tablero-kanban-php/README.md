# Tablero Kanban en PHP 🗂️

> ✅ **Terminado** — proyecto de 3 días (23-25 nov 2026). Ver [PLAN.md](PLAN.md).

Aplicación web para organizar tareas en **tableros Kanban** (estilo Trello), escrita en
**PHP puro + SQLite**, sin frameworks ni dependencias externas. Está pensada para ver por
dentro las piezas que normalmente esconde un framework: controlador frontal, router,
plantillas, PDO, transacciones, CSRF, respuestas JSON…

## Qué hace

- **Tableros**: crear, listar (con el número de tarjetas) y borrar. Cada tablero nuevo trae
  las columnas *Por hacer*, *En curso* y *Hecho*.
- **Tarjetas** con título, descripción, **etiqueta de color** (Urgente, Importante, En espera,
  Fácil, Idea, Bug) y **fecha límite**. Las vencidas se marcan en rojo y las que vencen hoy
  en naranja. Se pueden editar y borrar.
- **Mover tarjetas** entre columnas y reordenarlas con los botones ← ↑ ↓ → (funcionan sin
  JavaScript) o **arrastrando y soltando**.
- **Columnas**: añadir, renombrar, mover y borrar desde su menú `⋯` (mínimo 1, máximo 10).
- **Búsqueda y filtros**: texto (sin distinguir mayúsculas ni tildes: «camion» encuentra
  «Contratar camión»), etiqueta y estado de la fecha (vencidas, vencen hoy, con/sin fecha).
  Los filtros viven en la URL, así que se pueden guardar como marcador.
- **Estadísticas** del tablero: progreso (% de tarjetas en la última columna), tarjetas por
  columna y por etiqueta, vencidas y próximas fechas límite.
- **Exportar** a **CSV** (se abre en Excel/LibreOffice) o **JSON**. Si hay filtros activos,
  se exporta solo lo filtrado.
- **API JSON de solo lectura** para usar los datos desde otros programas.
- Validación con mensajes por campo, avisos tras cada acción, páginas de error 404/405/419,
  protección CSRF, escapado de todo el texto, modo oscuro automático y diseño para móvil.

## Cómo ejecutarlo

Necesitas PHP 8.1+ con la extensión `pdo_sqlite` (viene activada en casi todas las
instalaciones).

```bash
./iniciar.sh            # o: php -S localhost:8000 -t public public/index.php
# abre http://localhost:8000
```

La base de datos se crea sola en `datos/kanban.sqlite`. Para usar otra ruta:
`KANBAN_DB=/tmp/otra.sqlite ./iniciar.sh`.

### API

| Ruta | Devuelve |
|------|----------|
| `GET /api/tableros` | Lista de tableros con su número de tarjetas |
| `GET /api/tableros/{id}` | Tablero completo (columnas y tarjetas) + estadísticas |
| `GET /api/tableros/{id}?q=hotel&etiqueta=rojo&estado=vencidas` | Lo mismo, filtrado |
| `GET /tableros/{id}/exportar/csv` · `/exportar/json` | Descarga del tablero (acepta los mismos filtros) |

```bash
curl -s localhost:8000/api/tableros/1?estado=vencidas
# {"id":1,"nombre":"Mudanza",...,"columnas":[...],"filtro":{"estado":"vencidas"},"estadisticas":{...}}
```

Los errores también llegan en JSON: `{"ok": false, "error": "Ese tablero no existe"}` con
estado 404.

### Tests

```bash
php tests/ejecutar.php
```

**31 tests** con un mini runner propio (sin PHPUnit). Cada test usa SQLite **en memoria**:
repositorios, router, movimientos de tarjetas (las posiciones quedan siempre 0, 1, 2… sin
huecos), columnas, fechas, migración de una base antigua, filtros, estadísticas, CSV (comas,
comillas, saltos de línea y fórmulas peligrosas), API y la app completa simulando peticiones.

## Estructura

```
public/
  index.php        controlador frontal: todas las peticiones entran aquí
  estilos.css      CSS plano con modo claro/oscuro
  app.js           arrastrar y soltar (mejora progresiva con fetch)
src/
  App.php          rutas y lógica de cada página
  Router.php       "GET /tableros/{id}" → función
  Respuesta.php    estado + cabeceras + cuerpo (html, json, descarga o redirección 303)
  BaseDatos.php    conexión PDO a SQLite, tablas y migración
  Tableros.php     repositorio de tableros (y lectura del tablero completo)
  Columnas.php     añadir, renombrar, borrar y reordenar columnas
  Tarjetas.php     crear, editar, borrar y mover tarjetas
  Filtro.php       búsqueda y filtros a partir de la query string
  Estadisticas.php números del tablero (clase pura, sin BD)
  Exportador.php   tablero → JSON / CSV
  Vista.php        plantillas PHP dentro de un layout
  Csrf.php         token anti-CSRF en sesión
  funciones.php    e() para escapar HTML, normalizar(), url() y otras ayudas
vistas/            plantillas (layout, tableros, tablero, editar-tarjeta, estadisticas, error…)
tests/ejecutar.php mini runner de tests
```

## Qué se aprende

1. **Controlador frontal + router**: un único `index.php` recibe todas las peticiones y el
   router decide qué función ejecutar según el método y la URL (`/tableros/{id}`). Las
   respuestas son objetos (`Respuesta`), así la app se puede probar sin servidor.
2. **SQL seguro y consistente**: consultas preparadas contra la inyección SQL, claves
   foráneas con borrado en cascada y **transacciones** para operaciones "todo o nada"
   (crear un tablero con sus columnas, mover una tarjeta cerrando y abriendo huecos).
3. **Seguridad web básica**: escapado de salida con `htmlspecialchars` (XSS), token CSRF en
   cada formulario, patrón POST/Redirect/GET con `303` y **CSV sin inyección de fórmulas**
   (una celda que empieza por `=` se exporta como `'=`).
4. **Mejora progresiva y APIs**: todo funciona con formularios HTML normales; JavaScript solo
   añade el arrastrar y soltar. La misma lógica sirve HTML, descargas y una API JSON, y el
   estado de los filtros vive en la URL (`GET`), no en la sesión.
5. **Código testeable**: separar repositorios (SQL), clases puras (`Filtro`, `Estadisticas`,
   `Exportador`) y vistas permite probar cada pieza con datos de ejemplo y una BD en memoria.
