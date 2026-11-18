# biblioteca-api

✅ **Terminado** (3 días, del 16 al 18 de noviembre de 2026). Plan e hitos en [PLAN.md](PLAN.md).

API REST para gestionar los libros y préstamos de una biblioteca, con su **cliente de
terminal**, escrita en **Java puro**: sin Spring, sin Maven y sin ninguna librería externa.
El servidor HTTP es el del JDK, el JSON se procesa con una mini librería hecha a mano, los
datos se guardan en un fichero y el cliente usa el `HttpClient` estándar.

La idea es ver qué hay "debajo" de un framework: rutas, códigos de estado, validación,
serialización, persistencia y cómo se consume una API desde otro programa.

## Tecnologías

- Java 17 o superior (probado con Java 21): records, `switch` con flechas, pattern matching,
  bloques de texto
- `com.sun.net.httpserver.HttpServer` para el servidor
- `java.net.http.HttpClient` para el cliente y los tests de integración
- Scripts bash con `javac`/`java` (sin Maven ni Gradle) y un mini runner de tests propio

## Cómo ejecutarlo

Hace falta un JDK 17 o superior (`java -version`).

```bash
./ejecutar.sh                 # compila y arranca la API en http://localhost:8080
./ejecutar.sh --puerto 9000 --datos mis-datos.json
```

La primera vez se crean tres libros de ejemplo. Los datos se guardan en `datos/biblioteca.json`.

### Cliente de terminal

Con el servidor arrancado, desde otra terminal:

```bash
./cliente.sh listar
./cliente.sh crear --titulo "Ficciones" --autor "Jorge Luis Borges" --anio 1944
./cliente.sh prestar 2 "Ana López" --dias 7
./cliente.sh ver 2
./cliente.sh prestamos --vencidos
./cliente.sh devolver 2
./cliente.sh estadisticas
./cliente.sh --url http://localhost:9000 salud     # otro servidor (o BIBLIOTECA_URL=...)
```

Ejemplo de salida:

```
$ ./cliente.sh listar
ID  TÍTULO                    AUTOR                   AÑO   ESTADO
--  ------------------------  ----------------------  ----  ----------
1   Don Quijote de la Mancha  Miguel de Cervantes     1605  disponible
2   Cien años de soledad      Gabriel García Márquez  1967  prestado
3   Clean Code                Robert C. Martin        2008  disponible
3 libros

$ ./cliente.sh ver 2
  [2] Cien años de soledad
  Autor:  Gabriel García Márquez
  Año:    1967
  ISBN:   978-84-376-0495-4
  Estado: prestado
  Prestado a: Ana López hasta el 2026-11-25
```

| Comando | Qué hace |
|---------|----------|
| `listar [--buscar T] [--autor A] [--disponibles \| --prestados]` | Tabla de libros con filtros |
| `ver ID` | Ficha de un libro y, si está prestado, quién lo tiene |
| `crear --titulo T --autor A --anio N [--isbn I]` | Crea un libro |
| `editar ID [--titulo] [--autor] [--anio] [--isbn]` | Cambia solo los campos indicados (hace GET + PUT) |
| `borrar ID` | Borra un libro (no se puede si está prestado) |
| `prestar ID PERSONA [--dias N]` | Presta un libro (14 días por defecto, máximo 60) |
| `devolver ID` | Lo devuelve y avisa si fue con retraso |
| `prestamos [--vencidos]` | Préstamos activos o solo los atrasados |
| `estadisticas` | Resumen con barras por autor y por década |
| `salud` | Comprueba que el servidor responde |

Códigos de salida: `0` todo bien, `1` error de la API o de conexión (se muestra el código
HTTP y el mensaje), `2` uso incorrecto (se detecta antes de llamar a la API).

### La API con curl

| Método | Ruta | Qué hace | Respuestas |
|--------|------|----------|------------|
| GET | `/api/salud` | Comprueba que el servidor está vivo | 200 |
| GET | `/api/libros` | Lista libros (`?q=`, `?autor=`, `?disponible=true\|false`) | 200, 400 |
| POST | `/api/libros` | Crea un libro desde un cuerpo JSON | 201 + `Location`, 400, 413 |
| GET | `/api/libros/{id}` | Devuelve un libro | 200, 400, 404 |
| PUT | `/api/libros/{id}` | Reemplaza título, autor, año e ISBN | 200, 400, 404 |
| DELETE | `/api/libros/{id}` | Borra un libro | 204, 404, 409 (prestado) |
| POST | `/api/libros/{id}/prestamo` | Presta: `{"persona": "Ana", "dias": 14}` | 201, 400, 404, 409 |
| DELETE | `/api/libros/{id}/prestamo` | Devuelve el libro | 200, 404, 409 |
| GET | `/api/prestamos` | Préstamos activos (`?vencidos=true` para los atrasados) | 200 |
| GET | `/api/estadisticas` | Totales, vencidos, libros por autor y por década | 200 |

Los filtros se pueden combinar y no distinguen mayúsculas ni tildes (`?q=marquez` encuentra
"Márquez"). Todos los errores tienen la forma `{"error": "mensaje"}` y los 405 incluyen la
cabecera `Allow`.

```bash
curl http://localhost:8080/api/libros
curl -i -X POST http://localhost:8080/api/libros \
     -d '{"titulo":"Niebla","autor":"Miguel de Unamuno","anio":1914}'
curl "http://localhost:8080/api/libros?q=marquez&disponible=true"
curl -X POST http://localhost:8080/api/libros/2/prestamo -d '{"persona":"Ana","dias":7}'
curl http://localhost:8080/api/estadisticas
```

Un libro tiene `id`, `titulo` y `autor` (obligatorios), `anio` (entero entre 1000 y 2100),
`isbn` (opcional) y `disponible` (lo gestionan los préstamos; un `PUT` no lo cambia). Un
préstamo tiene `libroId`, `persona`, `fecha`, `devolverAntesDe` y `vencido`.

## Tests

```bash
./probar.sh
```

Ejecuta **67 pruebas** (todas pasan): la librería JSON, el modelo, el repositorio (búsqueda,
reglas de préstamo y persistencia en disco), pruebas de integración que arrancan el servidor
de verdad en un puerto libre y le hacen peticiones HTTP, y pruebas del cliente: `ClienteApi`
y el CLI completo ejecutado contra ese servidor, comprobando lo que imprime y su código de
salida. Se usa un reloj fijo para que las fechas (y los préstamos vencidos) sean
reproducibles. No hay JUnit: `Pruebas.java` incluye un mini runner casero.

## Estructura

```
src/biblioteca/
  Main.java                    punto de entrada del servidor: argumentos, ejemplos, arranque
  json/Json.java               mini librería JSON (parser descendente recursivo + escritor)
  modelo/Libro.java            record con validación y conversión a/desde mapas JSON
  modelo/Prestamo.java         record de un préstamo (fechas, vencido)
  modelo/ValidacionException.java      -> 400
  datos/RepositorioLibros.java libros y préstamos en memoria + guardado atómico en JSON
  datos/NoEncontradoException.java     -> 404
  datos/ConflictoException.java        -> 409
  api/Servidor.java            crea el HttpServer del JDK y registra las rutas
  api/Manejador.java           base de los handlers: excepciones -> códigos HTTP
  api/LibrosHandler.java       /api/libros (CRUD, filtros y préstamos)
  api/PrestamosHandler.java    /api/prestamos
  api/EstadisticasHandler.java /api/estadisticas
  api/SaludHandler.java        /api/salud
  api/Respuestas.java          leer cuerpos y parámetros, enviar respuestas JSON
  cliente/ClienteApi.java      cliente Java de la API (HttpClient + errores tipados)
  cliente/ClienteCli.java      cliente de terminal: subcomandos y salida legible
  cliente/Argumentos.java      lector de argumentos (--opcion valor, --marca, posicionales)
  cliente/Tabla.java           tablas de texto con columnas alineadas
test/biblioteca/Pruebas.java   tests unitarios, de integración y del cliente
compilar.sh  ejecutar.sh  probar.sh  cliente.sh
```

## Qué se aprende

1. **Cómo funciona una API REST por dentro.** Rutas, métodos HTTP, códigos de estado (201
   con `Location`, 204, 400, 404, 405 con `Allow`, 409, 413) y un formato de error común,
   sin que un framework lo esconda.
2. **Serializar y parsear JSON a mano.** Un parser descendente recursivo pequeño enseña qué
   hace realmente Jackson o Gson, incluidos los escapes y los números.
3. **Separar capas.** Modelo (validación), repositorio (datos y reglas de negocio) y API
   (HTTP); las excepciones de dominio se traducen a códigos HTTP en un único sitio
   (`Manejador`).
4. **Consumir una API desde otro programa.** `HttpClient`, codificar parámetros de URL
   (tildes y espacios), convertir respuestas de error en excepciones con código y mensaje, y
   distinguir "el servidor dijo que no" de "no hay servidor".
5. **Tests que se pueden repetir.** Puerto 0 para que el sistema elija uno libre, reloj fijo
   (`Clock`) para controlar las fechas y un CLI que recibe `PrintStream` y devuelve su código
   de salida para poder probarlo sin abrir procesos.
