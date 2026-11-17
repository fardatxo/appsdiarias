package biblioteca.api;

import biblioteca.datos.RepositorioLibros;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;

import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.Map;

/** GET /api/salud: comprobación rápida de que el servidor está vivo. */
class SaludHandler implements HttpHandler {

    private final RepositorioLibros repositorio;

    SaludHandler(RepositorioLibros repositorio) {
        this.repositorio = repositorio;
    }

    @Override
    public void handle(HttpExchange intercambio) throws IOException {
        if (!"GET".equals(intercambio.getRequestMethod())) {
            Respuestas.error(intercambio, 405, "Método no permitido");
            return;
        }
        Map<String, Object> cuerpo = new LinkedHashMap<>();
        cuerpo.put("estado", "ok");
        cuerpo.put("libros", repositorio.total());
        cuerpo.put("prestamos", repositorio.prestamosActivos().size());
        Respuestas.json(intercambio, 200, cuerpo);
    }
}
