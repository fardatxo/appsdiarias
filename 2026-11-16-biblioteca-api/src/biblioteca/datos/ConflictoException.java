package biblioteca.datos;

/** La operación choca con el estado actual, p. ej. prestar un libro ya prestado (409). */
public class ConflictoException extends RuntimeException {
    private static final long serialVersionUID = 1L;

    public ConflictoException(String mensaje) {
        super(mensaje);
    }
}
