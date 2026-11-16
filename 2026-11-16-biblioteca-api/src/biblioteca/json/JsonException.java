package biblioteca.json;

/** Error al leer un texto JSON mal formado. */
public class JsonException extends RuntimeException {
    public JsonException(String mensaje, int posicion) {
        super(mensaje + " (posición " + posicion + ")");
    }
}
