package biblioteca.api;

import biblioteca.json.Json;
import com.sun.net.httpserver.HttpExchange;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Map;

/** Utilidades para enviar respuestas JSON desde los handlers. */
final class Respuestas {

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

    /** Envía un error con el formato {"error": "..."} que usa toda la API. */
    static void error(HttpExchange intercambio, int estado, String mensaje) throws IOException {
        Map<String, Object> cuerpo = new LinkedHashMap<>();
        cuerpo.put("error", mensaje);
        json(intercambio, estado, cuerpo);
    }
}
