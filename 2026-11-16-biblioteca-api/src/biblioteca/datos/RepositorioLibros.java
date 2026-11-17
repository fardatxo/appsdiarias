package biblioteca.datos;

import biblioteca.json.Json;
import biblioteca.modelo.Libro;
import biblioteca.modelo.Prestamo;
import biblioteca.modelo.ValidacionException;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.text.Normalizer;
import java.time.Clock;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;

/**
 * Guarda los libros y los préstamos en memoria y, si se le da un fichero, los persiste en JSON
 * tras cada cambio. Todos los métodos públicos son synchronized porque el servidor atiende
 * peticiones en varios hilos a la vez.
 *
 * Formato del fichero:
 * {"siguienteId": 4, "libros": [ {...}, ... ], "prestamos": [ {...}, ... ]}
 */
public class RepositorioLibros {

    private final Map<Integer, Libro> libros = new LinkedHashMap<>();
    private final Map<Integer, Prestamo> prestamos = new LinkedHashMap<>(); // clave: id del libro
    private final Path fichero; // null = solo memoria (tests)
    private final Clock reloj;  // inyectable para probar fechas de préstamo
    private int siguienteId = 1;

    /** Repositorio solo en memoria. */
    public RepositorioLibros() {
        this(null, Clock.systemDefaultZone());
    }

    /** Repositorio que lee y guarda en el fichero indicado. */
    public RepositorioLibros(Path fichero) {
        this(fichero, Clock.systemDefaultZone());
    }

    public RepositorioLibros(Path fichero, Clock reloj) {
        this.fichero = fichero;
        this.reloj = reloj;
        if (fichero != null && Files.exists(fichero)) {
            cargar();
        }
    }

    // ---------------------------------------------------------------
    // Consultas
    // ---------------------------------------------------------------

    public synchronized List<Libro> listar() {
        return new ArrayList<>(libros.values());
    }

    /**
     * Filtra libros. Cualquier criterio puede ser null (= no filtrar por él).
     * @param texto      busca en título, autor e ISBN, sin distinguir mayúsculas ni tildes
     * @param autor      el autor contiene este texto
     * @param disponible solo disponibles (true) o solo prestados (false)
     */
    public synchronized List<Libro> buscar(String texto, String autor, Boolean disponible) {
        String t = normalizar(texto);
        String a = normalizar(autor);
        List<Libro> resultado = new ArrayList<>();
        for (Libro libro : libros.values()) {
            boolean coincideTexto = t.isEmpty()
                    || normalizar(libro.titulo()).contains(t)
                    || normalizar(libro.autor()).contains(t)
                    || normalizar(libro.isbn()).contains(t);
            boolean coincideAutor = a.isEmpty() || normalizar(libro.autor()).contains(a);
            boolean coincideDisponible = disponible == null || libro.disponible() == disponible;
            if (coincideTexto && coincideAutor && coincideDisponible) {
                resultado.add(libro);
            }
        }
        return resultado;
    }

    public synchronized Optional<Libro> buscarPorId(int id) {
        return Optional.ofNullable(libros.get(id));
    }

    public synchronized int total() {
        return libros.size();
    }

    public synchronized List<Prestamo> prestamosActivos() {
        return new ArrayList<>(prestamos.values());
    }

    public LocalDate hoy() {
        return LocalDate.now(reloj);
    }

    // ---------------------------------------------------------------
    // Libros: crear, actualizar, borrar
    // ---------------------------------------------------------------

    public synchronized Libro crear(String titulo, String autor, int anio, String isbn) {
        // Se construye (y valida) antes de gastar el id
        Libro libro = new Libro(siguienteId, titulo, autor, anio, isbn, true);
        return guardarNuevo(libro);
    }

    /** Crea un libro a partir de un cuerpo JSON ya leído. */
    public synchronized Libro crear(Map<String, Object> datos) {
        return guardarNuevo(Libro.desdeMapa(siguienteId, datos));
    }

    private Libro guardarNuevo(Libro libro) {
        libros.put(libro.id(), libro);
        siguienteId++;
        guardar();
        return libro;
    }

    /**
     * Reemplaza los datos de un libro (PUT). La disponibilidad no se cambia por aquí:
     * la controlan los préstamos, así que se conserva la que tenía.
     */
    public synchronized Libro actualizar(int id, Map<String, Object> datos) {
        Libro actual = obtener(id);
        Libro leido = Libro.desdeMapa(id, datos);
        Libro nuevo = new Libro(id, leido.titulo(), leido.autor(), leido.anio(), leido.isbn(), actual.disponible());
        libros.put(id, nuevo);
        guardar();
        return nuevo;
    }

    /** Borra un libro. No se puede borrar uno que está prestado. */
    public synchronized void borrar(int id) {
        obtener(id);
        if (prestamos.containsKey(id)) {
            throw new ConflictoException("No se puede borrar el libro " + id + ": está prestado");
        }
        libros.remove(id);
        guardar();
    }

    // ---------------------------------------------------------------
    // Préstamos
    // ---------------------------------------------------------------

    /** Presta un libro a una persona durante unos días. 409 si no está disponible. */
    public synchronized Prestamo prestar(int id, String persona, int dias) {
        Libro libro = obtener(id);
        if (dias < 1 || dias > Prestamo.DIAS_MAXIMOS) {
            throw new ValidacionException("Los días de préstamo deben estar entre 1 y " + Prestamo.DIAS_MAXIMOS);
        }
        if (!libro.disponible()) {
            throw new ConflictoException("El libro " + id + " no está disponible");
        }
        LocalDate hoy = hoy();
        Prestamo prestamo = new Prestamo(id, persona, hoy, hoy.plusDays(dias));
        prestamos.put(id, prestamo);
        libros.put(id, conDisponible(libro, false));
        guardar();
        return prestamo;
    }

    /** Devuelve un libro prestado. 409 si no estaba prestado. */
    public synchronized Prestamo devolver(int id) {
        Libro libro = obtener(id);
        Prestamo prestamo = prestamos.remove(id);
        if (prestamo == null) {
            throw new ConflictoException("El libro " + id + " no está prestado");
        }
        libros.put(id, conDisponible(libro, true));
        guardar();
        return prestamo;
    }

    // ---------------------------------------------------------------
    // Utilidades privadas
    // ---------------------------------------------------------------

    private Libro obtener(int id) {
        Libro libro = libros.get(id);
        if (libro == null) {
            throw new NoEncontradoException("No existe el libro con id " + id);
        }
        return libro;
    }

    private static Libro conDisponible(Libro l, boolean disponible) {
        return new Libro(l.id(), l.titulo(), l.autor(), l.anio(), l.isbn(), disponible);
    }

    /** Minúsculas y sin tildes: "Márquez" -> "marquez". */
    static String normalizar(String texto) {
        if (texto == null) {
            return "";
        }
        String sinTildes = Normalizer.normalize(texto.trim(), Normalizer.Form.NFD).replaceAll("\\p{M}", "");
        return sinTildes.toLowerCase(Locale.ROOT);
    }

    @SuppressWarnings("unchecked")
    private void cargar() {
        try {
            String texto = Files.readString(fichero, StandardCharsets.UTF_8);
            Map<String, Object> raiz = (Map<String, Object>) Json.leer(texto);
            for (Object o : (List<Object>) raiz.getOrDefault("libros", List.of())) {
                Map<String, Object> mapa = (Map<String, Object>) o;
                int id = ((Long) mapa.get("id")).intValue();
                libros.put(id, Libro.desdeMapa(id, mapa));
            }
            for (Object o : (List<Object>) raiz.getOrDefault("prestamos", List.of())) {
                Prestamo p = Prestamo.desdeMapa((Map<String, Object>) o);
                if (libros.containsKey(p.libroId())) {
                    prestamos.put(p.libroId(), p);
                }
            }
            int maximo = libros.keySet().stream().mapToInt(Integer::intValue).max().orElse(0);
            Object guardado = raiz.get("siguienteId");
            siguienteId = Math.max(maximo + 1, guardado instanceof Long l ? l.intValue() : 1);
        } catch (IOException e) {
            throw new UncheckedIOException("No se pudo leer " + fichero, e);
        } catch (ClassCastException | NullPointerException e) {
            throw new IllegalStateException("El fichero de datos " + fichero + " tiene un formato inesperado", e);
        }
    }

    private void guardar() {
        if (fichero == null) {
            return;
        }
        Map<String, Object> raiz = new LinkedHashMap<>();
        raiz.put("siguienteId", siguienteId);
        List<Object> listaLibros = new ArrayList<>();
        libros.values().forEach(l -> listaLibros.add(l.aMapa()));
        raiz.put("libros", listaLibros);
        List<Object> listaPrestamos = new ArrayList<>();
        prestamos.values().forEach(p -> listaPrestamos.add(p.aMapa()));
        raiz.put("prestamos", listaPrestamos);
        try {
            if (fichero.toAbsolutePath().getParent() != null) {
                Files.createDirectories(fichero.toAbsolutePath().getParent());
            }
            // Se escribe en un temporal y se renombra: si el programa se corta a medias,
            // el fichero bueno anterior sigue intacto.
            Path temporal = fichero.resolveSibling(fichero.getFileName() + ".tmp");
            Files.writeString(temporal, Json.escribir(raiz), StandardCharsets.UTF_8);
            Files.move(temporal, fichero, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException e) {
            throw new UncheckedIOException("No se pudo guardar " + fichero, e);
        }
    }
}
