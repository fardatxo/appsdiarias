package biblioteca.api;

import biblioteca.datos.RepositorioLibros;
import biblioteca.json.Json;
import biblioteca.json.JsonException;
import biblioteca.modelo.Libro;
import biblioteca.modelo.ValidacionException;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Rutas de libros:
 *   GET  /api/libros       -> lista todos los libros
 *   GET  /api/libros/{id}  -> devuelve un libro
 *   POST /api/libros       -> crea un libro a partir de un cuerpo JSON
 */
class LibrosHandler implements HttpHandler {

    private static final String BASE = "/api/libros";
    private static final int TAMANO_MAXIMO_CUERPO = 64 * 1024;

    private final RepositorioLibros repositorio;

    LibrosHandler(RepositorioLibros repositorio) {
        this.repositorio = repositorio;
    }

    @Override
    public void handle(HttpExchange intercambio) throws IOException {
        try {
            String ruta = intercambio.getRequestURI().getPath();
            String metodo = intercambio.getRequestMethod();
            // Lo que queda tras /api/libros: "" (colección) o "/7" (un libro)
            String resto = ruta.substring(BASE.length());
            if (resto.endsWith("/")) {
                resto = resto.substring(0, resto.length() - 1);
            }

            if (resto.isEmpty()) {
                switch (metodo) {
                    case "GET" -> listar(intercambio);
                    case "POST" -> crear(intercambio);
                    default -> Respuestas.error(intercambio, 405, "Método no permitido");
                }
            } else if (resto.startsWith("/") && resto.indexOf('/', 1) < 0) {
                if ("GET".equals(metodo)) {
                    obtener(intercambio, resto.substring(1));
                } else {
                    Respuestas.error(intercambio, 405, "Método no permitido");
                }
            } else {
                Respuestas.error(intercambio, 404, "Ruta no encontrada: " + ruta);
            }
        } catch (ValidacionException e) {
            Respuestas.error(intercambio, 400, e.getMessage());
        } catch (JsonException e) {
            Respuestas.error(intercambio, 400, "JSON no válido: " + e.getMessage());
        } catch (RuntimeException e) {
            // Fallo inesperado: lo registramos y respondemos 500 sin dar detalles internos
            System.err.println("Error interno: " + e);
            Respuestas.error(intercambio, 500, "Error interno del servidor");
        } finally {
            intercambio.close();
        }
    }

    private void listar(HttpExchange intercambio) throws IOException {
        List<Object> lista = new ArrayList<>();
        for (Libro libro : repositorio.listar()) {
            lista.add(libro.aMapa());
        }
        Respuestas.json(intercambio, 200, lista);
    }

    private void obtener(HttpExchange intercambio, String textoId) throws IOException {
        int id;
        try {
            id = Integer.parseInt(textoId);
        } catch (NumberFormatException e) {
            Respuestas.error(intercambio, 400, "El id debe ser un número: " + textoId);
            return;
        }
        Optional<Libro> libro = repositorio.buscarPorId(id);
        if (libro.isPresent()) {
            Respuestas.json(intercambio, 200, libro.get().aMapa());
        } else {
            Respuestas.error(intercambio, 404, "No existe el libro con id " + id);
        }
    }

    @SuppressWarnings("unchecked")
    private void crear(HttpExchange intercambio) throws IOException {
        // Leemos como mucho el máximo + 1 byte para detectar cuerpos demasiado grandes
        byte[] bytes = intercambio.getRequestBody().readNBytes(TAMANO_MAXIMO_CUERPO + 1);
        if (bytes.length > TAMANO_MAXIMO_CUERPO) {
            Respuestas.error(intercambio, 413, "El cuerpo de la petición es demasiado grande");
            return;
        }
        Object datos = Json.leer(new String(bytes, StandardCharsets.UTF_8));
        if (!(datos instanceof Map)) {
            throw new ValidacionException("El cuerpo debe ser un objeto JSON");
        }
        Libro creado = repositorio.crear((Map<String, Object>) datos);
        intercambio.getResponseHeaders().set("Location", BASE + "/" + creado.id());
        Respuestas.json(intercambio, 201, creado.aMapa());
    }
}
