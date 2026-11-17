package biblioteca.api;

import biblioteca.datos.ConflictoException;
import biblioteca.datos.NoEncontradoException;
import biblioteca.json.JsonException;
import biblioteca.modelo.ValidacionException;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;

import java.io.IOException;

/**
 * Base común de los handlers: convierte las excepciones en respuestas de error
 * con su código HTTP, para que cada ruta solo se ocupe del "camino feliz".
 */
abstract class Manejador implements HttpHandler {

    /** Atiende la petición; puede lanzar las excepciones de la aplicación. */
    protected abstract void atender(HttpExchange intercambio) throws IOException;

    @Override
    public final void handle(HttpExchange intercambio) throws IOException {
        try {
            atender(intercambio);
        } catch (ValidacionException e) {
            Respuestas.error(intercambio, 400, e.getMessage());
        } catch (JsonException e) {
            Respuestas.error(intercambio, 400, "JSON no válido: " + e.getMessage());
        } catch (NoEncontradoException e) {
            Respuestas.error(intercambio, 404, e.getMessage());
        } catch (ConflictoException e) {
            Respuestas.error(intercambio, 409, e.getMessage());
        } catch (RuntimeException e) {
            // Fallo inesperado: lo registramos y respondemos 500 sin dar detalles internos
            System.err.println("Error interno: " + e);
            Respuestas.error(intercambio, 500, "Error interno del servidor");
        } finally {
            intercambio.close();
        }
    }

    /** Responde 405 indicando qué métodos sí se admiten (cabecera Allow). */
    protected static void metodoNoPermitido(HttpExchange intercambio, String permitidos) throws IOException {
        intercambio.getResponseHeaders().set("Allow", permitidos);
        Respuestas.error(intercambio, 405, "Método no permitido. Usa: " + permitidos);
    }
}
