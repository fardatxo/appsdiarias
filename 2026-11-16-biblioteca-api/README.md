# biblioteca-api

🚧 **En curso — día 2 de 3.** Plan completo en [PLAN.md](PLAN.md).

API REST para gestionar los libros de una biblioteca, escrita en **Java puro**: sin Spring,
sin Maven y sin ninguna librería externa. El servidor HTTP es el del JDK, el JSON se procesa
con una mini librería hecha a mano y los datos se guardan en un fichero.

## Qué hace ya

| Método | Ruta | Qué hace | Respuestas |
|--------|------|----------|------------|
| GET | `/api/salud` | Comprueba que el servidor está vivo | 200 |
| GET | `/api/libros` | Lista los libros, con filtros opcionales | 200, 400 (filtro no válido) |
| POST | `/api/libros` | Crea un libro desde un cuerpo JSON | 201 + cabecera `Location`, 400 |
| GET | `/api/libros/{id}` | Devuelve un libro | 200, 400 (id no numérico), 404 |
| PUT | `/api/libros/{id}` | Reemplaza título, autor, año e ISBN | 200, 400, 404 |
| DELETE | `/api/libros/{id}` | Borra un libro | 204, 404, 409 (está prestado) |
| POST | `/api/libros/{id}/prestamo` | Presta el libro: `{"persona": "Ana", "dias": 14}` | 201, 400, 404, 409 (ya prestado) |
| DELETE | `/api/libros/{id}/prestamo` | Devuelve el libro | 200, 404, 409 (no estaba prestado) |
| GET | `/api/prestamos` | Préstamos activos (`?vencidos=true` para los atrasados) | 200 |

Filtros de `GET /api/libros` (se pueden combinar y no distinguen mayúsculas ni tildes):

- `?q=marquez` busca en título, autor e ISBN.
- `?autor=cortazar` filtra por autor.
- `?disponible=true` / `?disponible=false` solo libros libres o prestados.

Todos los errores tienen la misma forma: `{"error": "mensaje"}`. Los 405 incluyen la
cabecera `Allow` con los métodos que sí se pueden usar.

Un libro tiene `id`, `titulo` y `autor` (obligatorios), `anio` (entero entre 1000 y 2100),
`isbn` (opcional) y `disponible`. La disponibilidad la gestionan los préstamos: un `PUT` no
la cambia. Un préstamo tiene `libroId`, `persona`, `fecha`, `devolverAntesDe` (por defecto a
14 días, máximo 60) y `vencido`.

## Cómo ejecutarlo

Hace falta un JDK 17 o superior (`java -version`).

```bash
./ejecutar.sh                 # compila y arranca en http://localhost:8080
./ejecutar.sh --puerto 9000 --datos mis-datos.json
```

La primera vez se crean tres libros de ejemplo. Los datos se guardan en `datos/biblioteca.json`.

Pruébalo desde otra terminal:

```bash
curl http://localhost:8080/api/libros
curl http://localhost:8080/api/libros/1
curl -i -X POST http://localhost:8080/api/libros \
     -d '{"titulo":"Niebla","autor":"Miguel de Unamuno","anio":1914}'
curl "http://localhost:8080/api/libros?q=marquez&disponible=true"
curl -X POST http://localhost:8080/api/libros/2/prestamo -d '{"persona":"Ana","dias":7}'
curl http://localhost:8080/api/prestamos
curl -X DELETE http://localhost:8080/api/libros/2/prestamo
curl -i -X DELETE http://localhost:8080/api/libros/4
```

## Tests

```bash
./probar.sh
```

Ejecuta 50 pruebas: la librería JSON, el modelo, el repositorio (búsqueda, reglas de
préstamo y persistencia en disco, con un reloj fijo para que las fechas sean reproducibles) y pruebas de integración que arrancan el servidor de verdad en un puerto libre y le
hacen peticiones HTTP. No usan JUnit: `Pruebas.java` incluye un mini runner casero.

## Estructura

```
src/biblioteca/
  Main.java                  punto de entrada: argumentos, datos de ejemplo, arranque
  json/Json.java             mini librería JSON (parser descendente recursivo + escritor)
  json/JsonException.java
  modelo/Libro.java          record con validación y conversión a/desde mapas JSON
  modelo/Prestamo.java       record de un préstamo (fechas, vencido)
  modelo/ValidacionException.java     -> 400
  datos/RepositorioLibros.java   libros y préstamos en memoria + guardado atómico en JSON
  datos/NoEncontradoException.java    -> 404
  datos/ConflictoException.java       -> 409
  api/Servidor.java          crea el HttpServer del JDK y registra las rutas
  api/Manejador.java         base de los handlers: excepciones -> códigos HTTP
  api/LibrosHandler.java     rutas de /api/libros (CRUD, filtros y préstamos)
  api/PrestamosHandler.java  ruta /api/prestamos
  api/SaludHandler.java      ruta /api/salud
  api/Respuestas.java        leer cuerpos y parámetros, enviar respuestas JSON
test/biblioteca/Pruebas.java tests unitarios y de integración
compilar.sh  ejecutar.sh  probar.sh
```

## Qué viene después

- **Día 3:** cliente de terminal que consume la API (`listar`, `ver`, `crear`, `borrar`,
  `prestar`, `devolver`), pulido y README final.
