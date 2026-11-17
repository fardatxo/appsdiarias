package biblioteca.api;

import biblioteca.datos.NoEncontradoException;
import biblioteca.datos.RepositorioLibros;
import biblioteca.modelo.Libro;
import biblioteca.modelo.Prestamo;
import biblioteca.modelo.ValidacionException;
import com.sun.net.httpserver.HttpExchange;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Rutas de libros:
 *   GET    /api/libros                 -> lista (filtros: ?q=, ?autor=, ?disponible=true|false)
 *   POST   /api/libros                 -> crea un libro
 *   GET    /api/libros/{id}            -> devuelve un libro
 *   PUT    /api/libros/{id}            -> reemplaza título, autor, año e ISBN
 *   DELETE /api/libros/{id}            -> borra el libro (409 si está prestado)
 *   POST   /api/libros/{id}/prestamo   -> presta el libro: {"persona": "Ana", "dias": 14}
 *   DELETE /api/libros/{id}/prestamo   -> lo devuelve
 */
class LibrosHandler extends Manejador {

    private static final String BASE = "/api/libros";
    private static final Set<String> FILTROS = Set.of("q", "autor", "disponible");

    private final RepositorioLibros repositorio;
    private final PrestamosHandler prestamos;

    LibrosHandler(RepositorioLibros repositorio, PrestamosHandler prestamos) {
        this.repositorio = repositorio;
        this.prestamos = prestamos;
    }

    @Override
    protected void atender(HttpExchange intercambio) throws IOException {
        String ruta = intercambio.getRequestURI().getPath();
        String metodo = intercambio.getRequestMethod();
        // Lo que queda tras /api/libros, partido por "/": [] colección, [id] o [id, "prestamo"]
        String resto = ruta.substring(BASE.length());
        if (!resto.isEmpty() && !resto.startsWith("/")) {
            Respuestas.error(intercambio, 404, "Ruta no encontrada: " + ruta); // p. ej. /api/librosXYZ
            return;
        }
        String[] partes = resto.replaceAll("^/+|/+$", "").split("/");
        if (partes.length == 1 && partes[0].isEmpty()) {
            partes = new String[0];
        }

        if (partes.length == 0) {
            switch (metodo) {
                case "GET" -> listar(intercambio);
                case "POST" -> crear(intercambio);
                default -> metodoNoPermitido(intercambio, "GET, POST");
            }
        } else if (partes.length == 1) {
            int id = Respuestas.leerId(partes[0]);
            switch (metodo) {
                case "GET" -> obtener(intercambio, id);
                case "PUT" -> actualizar(intercambio, id);
                case "DELETE" -> borrar(intercambio, id);
                default -> metodoNoPermitido(intercambio, "GET, PUT, DELETE");
            }
        } else if (partes.length == 2 && partes[1].equals("prestamo")) {
            int id = Respuestas.leerId(partes[0]);
            switch (metodo) {
                case "POST" -> prestar(intercambio, id);
                case "DELETE" -> devolver(intercambio, id);
                default -> metodoNoPermitido(intercambio, "POST, DELETE");
            }
        } else {
            Respuestas.error(intercambio, 404, "Ruta no encontrada: " + ruta);
        }
    }

    // ---------------------------------------------------------------
    // Libros
    // ---------------------------------------------------------------

    private void listar(HttpExchange intercambio) throws IOException {
        Map<String, String> param = Respuestas.parametros(intercambio);
        for (String clave : param.keySet()) {
            if (!FILTROS.contains(clave)) {
                throw new ValidacionException("Filtro desconocido '" + clave + "'. Usa q, autor o disponible");
            }
        }
        List<Libro> encontrados = repositorio.buscar(param.get("q"), param.get("autor"),
                leerBooleano(param, "disponible"));
        List<Object> lista = new ArrayList<>();
        for (Libro libro : encontrados) {
            lista.add(libro.aMapa());
        }
        Respuestas.json(intercambio, 200, lista);
    }

    private void obtener(HttpExchange intercambio, int id) throws IOException {
        Libro libro = repositorio.buscarPorId(id)
                .orElseThrow(() -> new NoEncontradoException("No existe el libro con id " + id));
        Respuestas.json(intercambio, 200, libro.aMapa());
    }

    private void crear(HttpExchange intercambio) throws IOException {
        Map<String, Object> datos = Respuestas.leerObjeto(intercambio, false);
        if (datos == null) {
            return; // ya se respondió 413
        }
        Libro creado = repositorio.crear(datos);
        intercambio.getResponseHeaders().set("Location", BASE + "/" + creado.id());
        Respuestas.json(intercambio, 201, creado.aMapa());
    }

    private void actualizar(HttpExchange intercambio, int id) throws IOException {
        Map<String, Object> datos = Respuestas.leerObjeto(intercambio, false);
        if (datos == null) {
            return;
        }
        Respuestas.json(intercambio, 200, repositorio.actualizar(id, datos).aMapa());
    }

    private void borrar(HttpExchange intercambio, int id) throws IOException {
        repositorio.borrar(id);
        Respuestas.sinContenido(intercambio);
    }

    // ---------------------------------------------------------------
    // Préstamos
    // ---------------------------------------------------------------

    private void prestar(HttpExchange intercambio, int id) throws IOException {
        Map<String, Object> datos = Respuestas.leerObjeto(intercambio, false);
        if (datos == null) {
            return;
        }
        Object persona = datos.get("persona");
        if (!(persona instanceof String)) {
            throw new ValidacionException("El campo 'persona' es obligatorio y debe ser un texto");
        }
        Object dias = datos.getOrDefault("dias", (long) Prestamo.DIAS_POR_DEFECTO);
        if (!(dias instanceof Long)) {
            throw new ValidacionException("El campo 'dias' debe ser un número entero");
        }
        long valorDias = (Long) dias;
        // Comprobamos el rango aquí para no truncar al convertir a int
        if (valorDias < 1 || valorDias > Prestamo.DIAS_MAXIMOS) {
            throw new ValidacionException("Los días de préstamo deben estar entre 1 y " + Prestamo.DIAS_MAXIMOS);
        }
        Prestamo prestamo = repositorio.prestar(id, (String) persona, (int) valorDias);
        Respuestas.json(intercambio, 201, prestamos.conTitulo(prestamo, repositorio.hoy()));
    }

    private void devolver(HttpExchange intercambio, int id) throws IOException {
        Prestamo prestamo = repositorio.devolver(id);
        Respuestas.json(intercambio, 200, prestamos.conTitulo(prestamo, repositorio.hoy()));
    }

    /** Lee un parámetro true/false de la URL; null si no viene; 400 si trae otra cosa. */
    static Boolean leerBooleano(Map<String, String> param, String nombre) {
        String valor = param.get(nombre);
        if (valor == null || valor.isEmpty()) {
            return null;
        }
        return switch (valor.toLowerCase()) {
            case "true", "si", "sí" -> Boolean.TRUE;
            case "false", "no" -> Boolean.FALSE;
            default -> throw new ValidacionException("El parámetro '" + nombre + "' debe ser true o false");
        };
    }
}
