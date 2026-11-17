package biblioteca.datos;

/** El recurso pedido no existe (la API responde 404). */
public class NoEncontradoException extends RuntimeException {
    private static final long serialVersionUID = 1L;

    public NoEncontradoException(String mensaje) {
        super(mensaje);
    }
}
