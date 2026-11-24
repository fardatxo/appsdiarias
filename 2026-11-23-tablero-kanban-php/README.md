# Tablero Kanban en PHP 🗂️

> 🚧 **En curso** — día 2 de 3. Ver [PLAN.md](PLAN.md).

Aplicación web para organizar tareas en **tableros Kanban** (estilo Trello), escrita en
**PHP puro + SQLite**, sin frameworks ni dependencias externas.

## Qué hace ahora mismo

- Crear, listar y borrar tableros. Cada tablero nuevo trae las columnas
  *Por hacer*, *En curso* y *Hecho*.
- Ver un tablero con sus columnas y añadir tarjetas a cualquiera: título, descripción,
  **etiqueta de color** (Urgente, Importante, En espera, Fácil, Idea, Bug) y **fecha límite**.
- Las tarjetas vencidas se marcan en rojo y las que vencen hoy en naranja.
- Editar y borrar tarjetas.
- **Mover tarjetas** entre columnas y reordenarlas: con los botones ← ↑ ↓ → (funcionan sin
  JavaScript) o **arrastrando y soltando**.
- Gestionar columnas desde su menú `⋯`: añadir, renombrar, mover a izquierda/derecha y borrar
  (un tablero siempre conserva al menos una columna; máximo 10).
- Validación de formularios con mensajes por campo, avisos tras cada acción y páginas
  de error (404, 405, 419).
- Protección CSRF en todos los formularios y escapado de todo el texto del usuario.
- Modo oscuro automático y diseño que se adapta al móvil.

## Cómo ejecutarlo

Necesitas PHP 8.1+ con la extensión `pdo_sqlite` (viene activada en casi todas las
instalaciones).

```bash
./iniciar.sh            # o: php -S localhost:8000 -t public public/index.php
# abre http://localhost:8000
```

La base de datos se crea sola en `datos/kanban.sqlite`. Para usar otra ruta:
`KANBAN_DB=/tmp/otra.sqlite ./iniciar.sh`.

### Tests

```bash
php tests/ejecutar.php
```

Cada test usa una base de datos SQLite **en memoria**, así que no ensucian tus datos.
Hay 23 tests: repositorios, router, movimientos de tarjetas (comprobando que las posiciones
quedan siempre 0, 1, 2… sin huecos), columnas, fechas, migración de una base antigua y la
app completa simulando peticiones (también las respuestas JSON del arrastrar y soltar).

## Estructura

```
public/
  index.php        controlador frontal: todas las peticiones entran aquí
  estilos.css
  app.js           arrastrar y soltar (mejora progresiva con fetch)
src/
  App.php          rutas y lógica de cada página
  Router.php       "GET /tableros/{id}" → función
  Respuesta.php    estado + cabeceras + cuerpo (html o redirección 303)
  BaseDatos.php    conexión PDO a SQLite y creación de tablas
  Tableros.php     repositorio de tableros (y lectura del tablero completo)
  Columnas.php     añadir, renombrar, borrar y reordenar columnas
  Tarjetas.php     crear, editar, borrar y mover tarjetas
  Vista.php        plantillas PHP dentro de un layout
  Csrf.php         token anti-CSRF en sesión
  funciones.php    e() para escapar HTML y otras ayudas
vistas/            plantillas (layout, tableros, tablero, editar-tarjeta, campos-extra, error)
tests/ejecutar.php mini runner de tests
```

## Ideas clave (por ahora)

- **Controlador frontal + router**: un único `index.php` decide qué código ejecutar
  según el método y la URL.
- **Consultas preparadas** (`prepare` + `execute`) para evitar inyección SQL, y
  **transacciones** para crear un tablero y sus columnas "todo o nada".
- **POST/Redirect/GET**: tras guardar se responde con `303` para que recargar la página
  no reenvíe el formulario.
- **Escapado de salida** con `htmlspecialchars` para evitar XSS.
- **Mejora progresiva**: los botones ← ↑ ↓ → son formularios normales; `app.js` añade el
  arrastrar y soltar encima y manda el cambio con `fetch` (`ajax=1` → respuesta JSON).
- **Mantener un orden en SQL**: mover una tarjeta es "cerrar el hueco" en la columna de origen
  (`posicion - 1`) y "abrir hueco" en la de destino (`posicion + 1`), todo en una transacción.
- **Migraciones**: `PRAGMA table_info` dice qué columnas tiene la tabla y `ALTER TABLE`
  añade las que faltan, así una base creada el día 1 sigue funcionando.
