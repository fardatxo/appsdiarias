# biblioteca-api

🚧 **En curso — día 1 de 3.** Plan completo en [PLAN.md](PLAN.md).

API REST para gestionar los libros de una biblioteca, escrita en **Java puro**: sin Spring,
sin Maven y sin ninguna librería externa. El servidor HTTP es el del JDK, el JSON se procesa
con una mini librería hecha a mano y los datos se guardan en un fichero.

## Qué hace ya

| Método | Ruta | Qué hace | Respuestas |
|--------|------|----------|------------|
| GET | `/api/salud` | Comprueba que el servidor está vivo | 200 |
| GET | `/api/libros` | Lista todos los libros | 200 |
| GET | `/api/libros/{id}` | Devuelve un libro | 200, 400 (id no numérico), 404 |
| POST | `/api/libros` | Crea un libro desde un cuerpo JSON | 201 + cabecera `Location`, 400 (JSON roto o datos inválidos) |

Todos los errores tienen la misma forma: `{"error": "mensaje"}`.

Un libro tiene `id`, `titulo` y `autor` (obligatorios), `anio` (entero entre 1000 y 2100),
`isbn` (opcional) y `disponible`.

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
```

## Tests

```bash
./probar.sh
```

Ejecuta 29 pruebas: la librería JSON, el modelo y el repositorio (incluida la persistencia en
disco) y pruebas de integración que arrancan el servidor de verdad en un puerto libre y le
hacen peticiones HTTP. No usan JUnit: `Pruebas.java` incluye un mini runner casero.

## Estructura

```
src/biblioteca/
  Main.java                  punto de entrada: argumentos, datos de ejemplo, arranque
  json/Json.java             mini librería JSON (parser descendente recursivo + escritor)
  json/JsonException.java
  modelo/Libro.java          record con validación y conversión a/desde mapas JSON
  modelo/ValidacionException.java
  datos/RepositorioLibros.java   libros en memoria + guardado en fichero JSON
  api/Servidor.java          crea el HttpServer del JDK y registra las rutas
  api/LibrosHandler.java     rutas de /api/libros
  api/SaludHandler.java      ruta /api/salud
  api/Respuestas.java        envío de respuestas y errores en JSON
test/biblioteca/Pruebas.java tests unitarios y de integración
compilar.sh  ejecutar.sh  probar.sh
```

## Qué viene después

- **Día 2:** editar y borrar libros, búsqueda y filtros, y préstamos.
- **Día 3:** cliente de terminal que consume la API, pulido y README final.
