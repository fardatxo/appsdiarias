# PLAN — biblioteca-api

## Descripción

Una **API REST pequeña para gestionar una biblioteca** (libros y, más adelante, préstamos),
hecha en **Java puro, sin frameworks ni dependencias**: el servidor HTTP es el que trae el
JDK (`com.sun.net.httpserver`), el JSON se lee y escribe con una mini librería hecha a mano
y los datos se guardan en un fichero JSON. El último día se añade un cliente de terminal que
consume la API.

La idea es ver qué hay "debajo" de un framework como Spring: rutas, códigos de estado,
validación, serialización y persistencia, todo a la vista.

Proyecto del bloque A (lunes a miércoles): 3 hitos, uno por día.

## Tecnologías

- Java 17 o superior (probado con Java 21): records, `switch` con flechas, pattern matching
- `com.sun.net.httpserver.HttpServer` (servidor HTTP incluido en el JDK)
- `java.net.http.HttpClient` (cliente HTTP incluido en el JDK, para tests y para el cliente CLI)
- Scripts bash con `javac`/`java` (sin Maven ni Gradle)
- Tests con un mini runner propio (sin JUnit)

## Hitos

- [x] **Día 1 (lun 2026-11-16)** — Estructura base y primera API que funciona: mini librería
  JSON (lectura y escritura), modelo `Libro` con validación, repositorio en memoria con
  persistencia en fichero JSON, servidor con `GET /api/libros`, `GET /api/libros/{id}`,
  `POST /api/libros` y `GET /api/salud`, errores en JSON (400/404/405), tests unitarios y de
  integración, scripts y README inicial.
- [x] **Día 2 (mar 2026-11-17)** — CRUD completo y préstamos: `PUT` y `DELETE` de libros,
  búsqueda y filtros por query string (`?q=`, `?autor=`, `?disponible=`, sin distinguir
  mayúsculas ni tildes), y préstamos (`POST /api/libros/{id}/prestamo` para prestar a una
  persona, `DELETE` para devolver, `GET /api/prestamos` para ver los activos y
  `?vencidos=true`) con sus reglas (no prestar un libro ya prestado ni borrarlo, 409 en
  conflictos). Además: se arregla el `.gitignore` (la regla `datos/` dejaba fuera del repo
  `src/biblioteca/datos/RepositorioLibros.java` y el día 1 no compilaba desde un clon
  limpio), guardado atómico del fichero, clase base `Manejador` que traduce excepciones a
  400/404/409/500 y cabecera `Allow` en los 405. 50 tests en total.
- [ ] **Día 3 (mié 2026-11-18)** — Cliente y cierre: cliente de terminal (`listar`, `ver`,
  `crear`, `borrar`, `prestar`, `devolver`) que habla con la API, pulido (mensajes, casos
  límite), más tests y README final con "qué se aprende".

## Ideas extra (si sobra tiempo)

- Paginación de la lista (`?pagina=` y `?tamano=`).
- Estadísticas en `GET /api/estadisticas` (libros por autor, prestados vs. disponibles).
