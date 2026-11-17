package biblioteca.modelo;

import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Un préstamo activo: qué libro, a quién, cuándo se prestó y hasta cuándo.
 * Como Libro, es un record que se valida en el constructor.
 */
public record Prestamo(int libroId, String persona, LocalDate fecha, LocalDate devolverAntesDe) {

    public static final int DIAS_POR_DEFECTO = 14;
    public static final int DIAS_MAXIMOS = 60;
    public static final int LONGITUD_MAXIMA_PERSONA = 100;

    public Prestamo {
        persona = persona == null ? "" : persona.trim();
        if (persona.isEmpty()) {
            throw new ValidacionException("Hay que indicar a qué persona se presta el libro");
        }
        if (persona.length() > LONGITUD_MAXIMA_PERSONA) {
            throw new ValidacionException(
                    "El nombre de la persona no puede pasar de " + LONGITUD_MAXIMA_PERSONA + " caracteres");
        }
        if (fecha == null || devolverAntesDe == null || devolverAntesDe.isBefore(fecha)) {
            throw new ValidacionException("Fechas del préstamo no válidas");
        }
    }

    /** ¿Se ha pasado ya la fecha límite de devolución? */
    public boolean vencido(LocalDate hoy) {
        return hoy.isAfter(devolverAntesDe);
    }

    /** Mapa para el fichero de datos (sin campos calculados). */
    public Map<String, Object> aMapa() {
        Map<String, Object> mapa = new LinkedHashMap<>();
        mapa.put("libroId", libroId);
        mapa.put("persona", persona);
        mapa.put("fecha", fecha.toString());              // formato ISO: 2026-11-17
        mapa.put("devolverAntesDe", devolverAntesDe.toString());
        return mapa;
    }

    /** Mapa para la API: añade si está vencido según la fecha de hoy. */
    public Map<String, Object> aMapa(LocalDate hoy) {
        Map<String, Object> mapa = aMapa();
        mapa.put("vencido", vencido(hoy));
        return mapa;
    }

    /** Reconstruye un préstamo desde el fichero de datos. */
    public static Prestamo desdeMapa(Map<String, Object> mapa) {
        Object id = mapa.get("libroId");
        if (!(id instanceof Long)) {
            throw new ValidacionException("Préstamo sin 'libroId' numérico");
        }
        try {
            return new Prestamo(((Long) id).intValue(), (String) mapa.get("persona"),
                    LocalDate.parse((String) mapa.get("fecha")),
                    LocalDate.parse((String) mapa.get("devolverAntesDe")));
        } catch (RuntimeException e) {
            if (e instanceof ValidacionException v) {
                throw v;
            }
            throw new ValidacionException("Préstamo con datos no válidos: " + e.getMessage());
        }
    }
}
