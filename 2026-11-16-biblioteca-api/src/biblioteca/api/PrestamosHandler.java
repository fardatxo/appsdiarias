package biblioteca.api;

import biblioteca.datos.RepositorioLibros;
import biblioteca.modelo.Libro;
import biblioteca.modelo.Prestamo;
import com.sun.net.httpserver.HttpExchange;

import java.io.IOException;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * GET /api/prestamos           -> préstamos activos (con el título del libro y si está vencido)
 * GET /api/prestamos?vencidos=true -> solo los que ya deberían haberse devuelto
 */
class PrestamosHandler extends Manejador {

    private final RepositorioLibros repositorio;

    PrestamosHandler(RepositorioLibros repositorio) {
        this.repositorio = repositorio;
    }

    @Override
    protected void atender(HttpExchange intercambio) throws IOException {
        String ruta = intercambio.getRequestURI().getPath();
        if (!ruta.equals("/api/prestamos") && !ruta.equals("/api/prestamos/")) {
            Respuestas.error(intercambio, 404, "Ruta no encontrada: " + ruta);
            return;
        }
        if (!"GET".equals(intercambio.getRequestMethod())) {
            metodoNoPermitido(intercambio, "GET");
            return;
        }
        Boolean soloVencidos = LibrosHandler.leerBooleano(Respuestas.parametros(intercambio), "vencidos");
        LocalDate hoy = repositorio.hoy();
        List<Object> lista = new ArrayList<>();
        for (Prestamo p : repositorio.prestamosActivos()) {
            if (soloVencidos != null && p.vencido(hoy) != soloVencidos) {
                continue;
            }
            lista.add(conTitulo(p, hoy));
        }
        Respuestas.json(intercambio, 200, lista);
    }

    /** Añade el título del libro para que el cliente no tenga que pedirlo aparte. */
    Map<String, Object> conTitulo(Prestamo p, LocalDate hoy) {
        Map<String, Object> mapa = p.aMapa(hoy);
        mapa.put("titulo", repositorio.buscarPorId(p.libroId()).map(Libro::titulo).orElse(""));
        return mapa;
    }
}
