package biblioteca.cliente;

import biblioteca.json.Json;
import biblioteca.json.JsonException;

import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Cliente Java de la API: cada método hace una petición HTTP y devuelve el JSON ya leído
 * (mapas y listas). Si la API responde con un error, lanza {@link ErrorApi} con su código
 * y su mensaje; si no se puede conectar, lanza IOException.
 */
public class ClienteApi {

    private final String base;
    private final HttpClient http;

    /** @param base dirección del servidor, p. ej. "http://localhost:8080" */
    public ClienteApi(String base) {
        // Quitamos la barra final para poder concatenar rutas sin dobles barras
        this.base = base.replaceAll("/+$", "");
        this.http = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(3))
                .proxy(HttpClient.Builder.NO_PROXY) // la API suele estar en local: sin proxy
                .build();
    }

    // ---------------------------------------------------------------
    // Operaciones de la API
    // ---------------------------------------------------------------

    public Map<String, Object> salud() throws IOException {
        return objeto(enviar("GET", "/api/salud", null));
    }

    /** Lista libros. Los filtros nulos o vacíos no se envían. */
    public List<Object> listar(String texto, String autor, Boolean disponible) throws IOException {
        Map<String, String> filtros = new LinkedHashMap<>();
        filtros.put("q", texto);
        filtros.put("autor", autor);
        filtros.put("disponible", disponible == null ? null : disponible.toString());
        return lista(enviar("GET", "/api/libros" + consulta(filtros), null));
    }

    public Map<String, Object> ver(int id) throws IOException {
        return objeto(enviar("GET", "/api/libros/" + id, null));
    }

    public Map<String, Object> crear(Map<String, Object> libro) throws IOException {
        return objeto(enviar("POST", "/api/libros", libro));
    }

    public Map<String, Object> actualizar(int id, Map<String, Object> libro) throws IOException {
        return objeto(enviar("PUT", "/api/libros/" + id, libro));
    }

    public void borrar(int id) throws IOException {
        enviar("DELETE", "/api/libros/" + id, null);
    }

    public Map<String, Object> prestar(int id, String persona, Integer dias) throws IOException {
        Map<String, Object> cuerpo = new LinkedHashMap<>();
        cuerpo.put("persona", persona);
        if (dias != null) {
            cuerpo.put("dias", dias);
        }
        return objeto(enviar("POST", "/api/libros/" + id + "/prestamo", cuerpo));
    }

    public Map<String, Object> devolver(int id) throws IOException {
        return objeto(enviar("DELETE", "/api/libros/" + id + "/prestamo", null));
    }

    public List<Object> prestamos(boolean soloVencidos) throws IOException {
        return lista(enviar("GET", "/api/prestamos" + (soloVencidos ? "?vencidos=true" : ""), null));
    }

    public Map<String, Object> estadisticas() throws IOException {
        return objeto(enviar("GET", "/api/estadisticas", null));
    }

    // ---------------------------------------------------------------
    // HTTP
    // ---------------------------------------------------------------

    /** Hace la petición y devuelve el JSON de la respuesta (null si viene vacía). */
    private Object enviar(String metodo, String ruta, Object cuerpo) throws IOException {
        HttpRequest.BodyPublisher publicador = cuerpo == null
                ? HttpRequest.BodyPublishers.noBody()
                : HttpRequest.BodyPublishers.ofString(Json.escribir(cuerpo), StandardCharsets.UTF_8);
        HttpRequest.Builder peticion;
        try {
            peticion = HttpRequest.newBuilder(URI.create(base + ruta))
                    .timeout(Duration.ofSeconds(10))
                    .method(metodo, publicador);
        } catch (IllegalArgumentException e) {
            throw new IOException("URL no válida: " + base + ruta);
        }
        if (cuerpo != null) {
            peticion.header("Content-Type", "application/json; charset=utf-8");
        }

        HttpResponse<String> respuesta;
        try {
            respuesta = http.send(peticion.build(), HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IOException("Petición interrumpida");
        }

        String texto = respuesta.body();
        Object json = null;
        if (texto != null && !texto.isBlank()) {
            try {
                json = Json.leer(texto);
            } catch (JsonException e) {
                throw new IOException("El servidor no ha respondido con JSON válido");
            }
        }
        int estado = respuesta.statusCode();
        if (estado >= 400) {
            String mensaje = json instanceof Map<?, ?> m && m.get("error") instanceof String s
                    ? s : "Error HTTP " + estado;
            throw new ErrorApi(estado, mensaje);
        }
        return json;
    }

    /** Construye "?q=...&autor=..." codificando los valores (tildes, espacios...). */
    static String consulta(Map<String, String> parametros) {
        StringBuilder sb = new StringBuilder();
        for (Map.Entry<String, String> e : parametros.entrySet()) {
            if (e.getValue() == null || e.getValue().isBlank()) {
                continue;
            }
            sb.append(sb.length() == 0 ? '?' : '&')
                    .append(e.getKey()).append('=')
                    .append(URLEncoder.encode(e.getValue(), StandardCharsets.UTF_8));
        }
        return sb.toString();
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> objeto(Object json) throws IOException {
        if (json instanceof Map) {
            return (Map<String, Object>) json;
        }
        throw new IOException("Se esperaba un objeto JSON en la respuesta");
    }

    @SuppressWarnings("unchecked")
    private static List<Object> lista(Object json) throws IOException {
        if (json instanceof List) {
            return (List<Object>) json;
        }
        throw new IOException("Se esperaba una lista JSON en la respuesta");
    }

    /** Error devuelto por la API (código 4xx o 5xx con su mensaje). */
    public static class ErrorApi extends IOException {
        private static final long serialVersionUID = 1L;
        private final int estado;

        public ErrorApi(int estado, String mensaje) {
            super(mensaje);
            this.estado = estado;
        }

        public int estado() {
            return estado;
        }
    }
}
