package biblioteca.modelo;

/** Los datos recibidos no cumplen las reglas del modelo (título vacío, año absurdo...). */
public class ValidacionException extends RuntimeException {
    private static final long serialVersionUID = 1L;

    public ValidacionException(String mensaje) {
        super(mensaje);
    }
}
