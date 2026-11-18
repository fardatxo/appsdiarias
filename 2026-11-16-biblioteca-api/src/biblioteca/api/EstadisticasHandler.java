package biblioteca.api;

import biblioteca.datos.RepositorioLibros;
import biblioteca.modelo.Libro;
import biblioteca.modelo.Prestamo;
import com.sun.net.httpserver.HttpExchange;

import java.io.IOException;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * GET /api/estadisticas -> resumen de la biblioteca:
 *   total de libros, disponibles, prestados, préstamos vencidos,
 *   libros por autor (de más a menos) y libros por década.
 */
class EstadisticasHandler extends Manejador {

    private final RepositorioLibros repositorio;

    EstadisticasHandler(RepositorioLibros repositorio) {
        this.repositorio = repositorio;
    }

    @Override
    protected void atender(HttpExchange intercambio) throws IOException {
        String ruta = intercambio.getRequestURI().getPath();
        if (!ruta.equals("/api/estadisticas") && !ruta.equals("/api/estadisticas/")) {
            Respuestas.error(intercambio, 404, "Ruta no encontrada: " + ruta);
            return;
        }
        if (!"GET".equals(intercambio.getRequestMethod())) {
            metodoNoPermitido(intercambio, "GET");
            return;
        }
        Respuestas.json(intercambio, 200, calcular(repositorio.listar(), repositorio.prestamosActivos(),
                repositorio.hoy()));
    }

    /** Cálculo puro (sin HTTP) para poder probarlo fácilmente. */
    static Map<String, Object> calcular(List<Libro> libros, List<Prestamo> prestamos, LocalDate hoy) {
        int disponibles = 0;
        Map<String, Integer> porAutor = new LinkedHashMap<>();
        Map<Integer, Integer> porDecada = new TreeMap<>(); // TreeMap: décadas ordenadas
        for (Libro libro : libros) {
            if (libro.disponible()) {
                disponibles++;
            }
            porAutor.merge(libro.autor(), 1, Integer::sum);
            porDecada.merge(libro.anio() / 10 * 10, 1, Integer::sum);
        }
        int vencidos = 0;
        for (Prestamo p : prestamos) {
            if (p.vencido(hoy)) {
                vencidos++;
            }
        }

        // Autores de más libros a menos; a igualdad, por orden alfabético
        List<Map.Entry<String, Integer>> autores = new ArrayList<>(porAutor.entrySet());
        autores.sort(Map.Entry.<String, Integer>comparingByValue(Comparator.reverseOrder())
                .thenComparing(Map.Entry.comparingByKey()));
        List<Object> listaAutores = new ArrayList<>();
        for (Map.Entry<String, Integer> e : autores) {
            Map<String, Object> fila = new LinkedHashMap<>();
            fila.put("autor", e.getKey());
            fila.put("libros", e.getValue());
            listaAutores.add(fila);
        }
        Map<String, Object> decadas = new LinkedHashMap<>();
        porDecada.forEach((decada, cuantos) -> decadas.put(decada + "s", cuantos));

        Map<String, Object> resultado = new LinkedHashMap<>();
        resultado.put("libros", libros.size());
        resultado.put("disponibles", disponibles);
        resultado.put("prestados", libros.size() - disponibles);
        resultado.put("vencidos", vencidos);
        resultado.put("porAutor", listaAutores);
        resultado.put("porDecada", decadas);
        return resultado;
    }
}
