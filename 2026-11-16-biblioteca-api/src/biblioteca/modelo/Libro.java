package biblioteca.modelo;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Un libro de la biblioteca. Es un record: inmutable y con equals/hashCode/toString gratis.
 * El constructor compacto valida y limpia los datos, así nunca existe un Libro inválido.
 */
public record Libro(int id, String titulo, String autor, int anio, String isbn, boolean disponible) {

    public static final int ANIO_MINIMO = 1000;
    public static final int ANIO_MAXIMO = 2100;

    public Libro {
        titulo = limpiar(titulo);
        autor = limpiar(autor);
        isbn = limpiar(isbn);
        if (titulo.isEmpty()) {
            throw new ValidacionException("El título es obligatorio");
        }
        if (autor.isEmpty()) {
            throw new ValidacionException("El autor es obligatorio");
        }
        if (anio < ANIO_MINIMO || anio > ANIO_MAXIMO) {
            throw new ValidacionException(
                    "El año debe estar entre " + ANIO_MINIMO + " y " + ANIO_MAXIMO);
        }
    }

    private static String limpiar(String texto) {
        return texto == null ? "" : texto.trim();
    }

    /** Convierte el libro en un mapa listo para escribirse como JSON. */
    public Map<String, Object> aMapa() {
        Map<String, Object> mapa = new LinkedHashMap<>();
        mapa.put("id", id);
        mapa.put("titulo", titulo);
        mapa.put("autor", autor);
        mapa.put("anio", anio);
        mapa.put("isbn", isbn);
        mapa.put("disponible", disponible);
        return mapa;
    }

    /**
     * Crea un libro a partir de un mapa leído de JSON.
     * Comprueba los tipos uno a uno para dar mensajes de error claros.
     */
    public static Libro desdeMapa(int id, Map<String, Object> mapa) {
        String titulo = texto(mapa, "titulo", true);
        String autor = texto(mapa, "autor", true);
        String isbn = texto(mapa, "isbn", false);
        Object anio = mapa.get("anio");
        if (!(anio instanceof Long)) {
            throw new ValidacionException("El campo 'anio' es obligatorio y debe ser un número entero");
        }
        long valorAnio = (Long) anio;
        if (valorAnio < ANIO_MINIMO || valorAnio > ANIO_MAXIMO) {
            throw new ValidacionException(
                    "El año debe estar entre " + ANIO_MINIMO + " y " + ANIO_MAXIMO);
        }
        Object disponible = mapa.get("disponible");
        if (disponible != null && !(disponible instanceof Boolean)) {
            throw new ValidacionException("El campo 'disponible' debe ser true o false");
        }
        // Un libro nuevo está disponible salvo que se diga lo contrario
        boolean estaDisponible = disponible == null || (Boolean) disponible;
        return new Libro(id, titulo, autor, (int) valorAnio, isbn, estaDisponible);
    }

    private static String texto(Map<String, Object> mapa, String campo, boolean obligatorio) {
        Object valor = mapa.get(campo);
        if (valor == null) {
            if (obligatorio) {
                throw new ValidacionException("Falta el campo '" + campo + "'");
            }
            return "";
        }
        if (!(valor instanceof String)) {
            throw new ValidacionException("El campo '" + campo + "' debe ser un texto");
        }
        return (String) valor;
    }
}
