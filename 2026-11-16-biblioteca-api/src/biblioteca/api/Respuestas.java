package biblioteca.api;

import biblioteca.json.Json;
import biblioteca.modelo.ValidacionException;
import com.sun.net.httpserver.HttpExchange;

import java.io.IOException;
import java.io.OutputStream;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Map;

/** Utilidades compartidas por los handlers: leer peticiones y enviar respuestas JSON. */
final class Respuestas {

    /** Tamaño máximo del cuerpo de una petición (64 KB): de sobra para un libro. */
    static final int TAMANO_MAXIMO_CUERPO = 64 * 1024;

    private Respuestas() {
    }

    /** Envía un valor como JSON con el código de estado indicado. */
    static void json(HttpExchange intercambio, int estado, Object valor) throws IOException {
        byte[] cuerpo = Json.escribir(valor).getBytes(StandardCharsets.UTF_8);
        intercambio.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        intercambio.sendResponseHeaders(estado, cuerpo.length);
        try (OutputStream salida = intercambio.getResponseBody()) {
            salida.write(cuerpo);
        }
    }

    /** Respuesta sin cuerpo (p. ej. 204 tras borrar). */
    static void sinContenido(HttpExchange intercambio) throws IOException {
        intercambio.sendResponseHeaders(204, -1);
    }

    /** Envía un error con el formato {"error": "..."} que usa toda la API. */
    static void error(HttpExchange intercambio, int estado, String mensaje) throws IOException {
        Map<String, Object> cuerpo = new LinkedHashMap<>();
        cuerpo.put("error", mensaje);
        json(intercambio, estado, cuerpo);
    }

    /**
     * Lee el cuerpo como objeto JSON. Devuelve null si es demasiado grande
     * (y ya ha respondido 413); lanza ValidacionException si no es un objeto.
     */
    @SuppressWarnings("unchecked")
    static Map<String, Object> leerObjeto(HttpExchange intercambio, boolean vacioPermitido) throws IOException {
        // Leemos como mucho el máximo + 1 byte para detectar cuerpos demasiado grandes
        byte[] bytes = intercambio.getRequestBody().readNBytes(TAMANO_MAXIMO_CUERPO + 1);
        if (bytes.length > TAMANO_MAXIMO_CUERPO) {
            error(intercambio, 413, "El cuerpo de la petición es demasiado grande");
            return null;
        }
        String texto = new String(bytes, StandardCharsets.UTF_8);
        if (vacioPermitido && texto.isBlank()) {
            return new LinkedHashMap<>();
        }
        Object datos = Json.leer(texto);
        if (!(datos instanceof Map)) {
            throw new ValidacionException("El cuerpo debe ser un objeto JSON");
        }
        return (Map<String, Object>) datos;
    }

    /** Convierte "q=hola&autor=Garc%C3%ADa" en un mapa ya decodificado. */
    static Map<String, String> parametros(HttpExchange intercambio) {
        Map<String, String> resultado = new LinkedHashMap<>();
        String consulta = intercambio.getRequestURI().getRawQuery();
        if (consulta == null || consulta.isEmpty()) {
            return resultado;
        }
        for (String par : consulta.split("&")) {
            if (par.isEmpty()) {
                continue;
            }
            int igual = par.indexOf('=');
            String clave = igual < 0 ? par : par.substring(0, igual);
            String valor = igual < 0 ? "" : par.substring(igual + 1);
            try {
                resultado.put(URLDecoder.decode(clave, StandardCharsets.UTF_8),
                        URLDecoder.decode(valor, StandardCharsets.UTF_8));
            } catch (IllegalArgumentException e) {
                throw new ValidacionException("Parámetro mal codificado: " + par);
            }
        }
        return resultado;
    }

    /** Convierte un texto de la URL en id numérico o lanza ValidacionException (400). */
    static int leerId(String texto) {
        try {
            return Integer.parseInt(texto);
        } catch (NumberFormatException e) {
            throw new ValidacionException("El id debe ser un número: " + texto);
        }
    }
}
