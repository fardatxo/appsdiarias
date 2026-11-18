package biblioteca.cliente;

import java.io.IOException;
import java.io.PrintStream;
import java.net.ConnectException;
import java.net.http.HttpConnectTimeoutException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Cliente de terminal de la biblioteca: traduce subcomandos a peticiones a la API
 * y muestra las respuestas como tablas legibles.
 *
 * Uso: java -cp out biblioteca.cliente.ClienteCli [--url http://localhost:8080] COMANDO [args]
 */
public class ClienteCli {

    /** Códigos de salida: 0 bien, 1 error de la API o de conexión, 2 uso incorrecto. */
    static final int OK = 0;
    static final int ERROR = 1;
    static final int USO = 2;

    private static final String AYUDA = """
            Cliente de la Biblioteca API

            Uso: ./cliente.sh [--url URL] COMANDO [argumentos]

            Comandos:
              listar [--buscar TEXTO] [--autor AUTOR] [--disponibles | --prestados]
              ver ID
              crear --titulo T --autor A --anio N [--isbn I]
              editar ID [--titulo T] [--autor A] [--anio N] [--isbn I]
              borrar ID
              prestar ID PERSONA [--dias N]
              devolver ID
              prestamos [--vencidos]
              estadisticas
              salud
              ayuda

            La URL por defecto es http://localhost:8080 (o la variable BIBLIOTECA_URL).""";

    private final PrintStream out;
    private final PrintStream err;

    public ClienteCli(PrintStream out, PrintStream err) {
        this.out = out;
        this.err = err;
    }

    public static void main(String[] args) {
        System.exit(new ClienteCli(System.out, System.err).ejecutar(args));
    }

    /** Ejecuta un comando completo y devuelve el código de salida (así se puede probar). */
    public int ejecutar(String[] args) {
        String url = System.getenv().getOrDefault("BIBLIOTECA_URL", "http://localhost:8080");
        List<String> resto = new ArrayList<>(List.of(args));
        if (resto.size() >= 2 && resto.get(0).equals("--url")) {
            url = resto.get(1);
            resto = resto.subList(2, resto.size());
        }
        if (resto.isEmpty() || Set.of("ayuda", "--ayuda", "-h", "help").contains(resto.get(0))) {
            out.println(AYUDA);
            return resto.isEmpty() ? USO : OK;
        }

        String comando = resto.get(0);
        Argumentos a;
        try {
            a = Argumentos.leer(resto.subList(1, resto.size()));
        } catch (IllegalArgumentException e) {
            err.println("Error: " + e.getMessage());
            return USO;
        }

        ClienteApi api = new ClienteApi(url);
        try {
            switch (comando) {
                case "listar" -> listar(api, a);
                case "ver" -> ver(api, a);
                case "crear" -> crear(api, a);
                case "editar" -> editar(api, a);
                case "borrar" -> borrar(api, a);
                case "prestar" -> prestar(api, a);
                case "devolver" -> devolver(api, a);
                case "prestamos" -> prestamos(api, a);
                case "estadisticas" -> estadisticas(api, a);
                case "salud" -> salud(api, a);
                default -> throw new IllegalArgumentException(
                        "Comando desconocido: " + comando + " (usa 'ayuda' para ver la lista)");
            }
            return OK;
        } catch (IllegalArgumentException e) {
            err.println("Error: " + e.getMessage());
            return USO;
        } catch (ClienteApi.ErrorApi e) {
            err.println("Error " + e.estado() + ": " + e.getMessage());
            return ERROR;
        } catch (ConnectException | HttpConnectTimeoutException e) {
            err.println("No se puede conectar con " + url + ". ¿Está arrancado el servidor (./ejecutar.sh)?");
            return ERROR;
        } catch (IOException e) {
            err.println("Error de comunicación: " + (e.getMessage() == null ? e : e.getMessage()));
            return ERROR;
        }
    }

    // ---------------------------------------------------------------
    // Comandos
    // ---------------------------------------------------------------

    private void listar(ClienteApi api, Argumentos a) throws IOException {
        a.soloOpciones("buscar", "autor", "disponibles", "prestados");
        a.sinPosicionales(0);
        if (a.marca("disponibles") && a.marca("prestados")) {
            throw new IllegalArgumentException("Usa --disponibles o --prestados, no los dos");
        }
        Boolean disponible = a.marca("disponibles") ? Boolean.TRUE : a.marca("prestados") ? Boolean.FALSE : null;
        List<Object> libros = api.listar(a.opcion("buscar"), a.opcion("autor"), disponible);
        if (libros.isEmpty()) {
            out.println("No hay libros que coincidan.");
            return;
        }
        Tabla tabla = new Tabla("ID", "TÍTULO", "AUTOR", "AÑO", "ESTADO");
        for (Object o : libros) {
            Map<?, ?> l = (Map<?, ?>) o;
            tabla.fila(l.get("id"), l.get("titulo"), l.get("autor"), l.get("anio"),
                    Boolean.TRUE.equals(l.get("disponible")) ? "disponible" : "prestado");
        }
        tabla.imprimir(out);
        out.println(libros.size() + (libros.size() == 1 ? " libro" : " libros"));
    }

    private void ver(ClienteApi api, Argumentos a) throws IOException {
        a.soloOpciones();
        int id = a.id();
        Map<String, Object> l = api.ver(id);
        imprimirLibro(l);
        if (!Boolean.TRUE.equals(l.get("disponible"))) {
            // Buscamos su préstamo para mostrar quién lo tiene
            for (Object o : api.prestamos(false)) {
                Map<?, ?> p = (Map<?, ?>) o;
                if (p.get("libroId") instanceof Number n && n.intValue() == id) {
                    out.println("  Prestado a: " + p.get("persona") + " hasta el " + p.get("devolverAntesDe")
                            + (Boolean.TRUE.equals(p.get("vencido")) ? "  (¡VENCIDO!)" : ""));
                }
            }
        }
    }

    private void crear(ClienteApi api, Argumentos a) throws IOException {
        a.soloOpciones("titulo", "autor", "anio", "isbn");
        a.sinPosicionales(0);
        Map<String, Object> libro = new LinkedHashMap<>();
        libro.put("titulo", a.obligatoria("titulo"));
        libro.put("autor", a.obligatoria("autor"));
        libro.put("anio", a.entero("anio", true));
        if (a.opcion("isbn") != null) {
            libro.put("isbn", a.opcion("isbn"));
        }
        Map<String, Object> creado = api.crear(libro);
        out.println("Libro creado con id " + creado.get("id") + ":");
        imprimirLibro(creado);
    }

    /** Edita solo los campos indicados: pide el libro, cambia esos campos y hace PUT. */
    private void editar(ClienteApi api, Argumentos a) throws IOException {
        a.soloOpciones("titulo", "autor", "anio", "isbn");
        int id = a.id();
        if (a.opcion("titulo") == null && a.opcion("autor") == null
                && a.opcion("anio") == null && a.opcion("isbn") == null) {
            throw new IllegalArgumentException("Indica al menos un campo a cambiar (--titulo, --autor, --anio o --isbn)");
        }
        Integer anio = a.entero("anio", false);
        Map<String, Object> actual = api.ver(id);
        Map<String, Object> nuevo = new LinkedHashMap<>();
        nuevo.put("titulo", a.opcion("titulo") != null ? a.opcion("titulo") : actual.get("titulo"));
        nuevo.put("autor", a.opcion("autor") != null ? a.opcion("autor") : actual.get("autor"));
        nuevo.put("anio", anio != null ? anio : actual.get("anio"));
        nuevo.put("isbn", a.opcion("isbn") != null ? a.opcion("isbn") : actual.get("isbn"));
        out.println("Libro actualizado:");
        imprimirLibro(api.actualizar(id, nuevo));
    }

    private void borrar(ClienteApi api, Argumentos a) throws IOException {
        a.soloOpciones();
        int id = a.id();
        api.borrar(id);
        out.println("Libro " + id + " borrado.");
    }

    private void prestar(ClienteApi api, Argumentos a) throws IOException {
        a.soloOpciones("dias");
        a.sinPosicionales(2);
        if (a.posicionales().size() < 2) {
            throw new IllegalArgumentException("Uso: prestar ID PERSONA [--dias N]");
        }
        int id = Argumentos.leerId(a.posicionales().get(0));
        Map<String, Object> p = api.prestar(id, a.posicionales().get(1), a.entero("dias", false));
        out.println("Prestado «" + p.get("titulo") + "» a " + p.get("persona")
                + ". Devolver antes del " + p.get("devolverAntesDe") + ".");
    }

    private void devolver(ClienteApi api, Argumentos a) throws IOException {
        a.soloOpciones();
        Map<String, Object> p = api.devolver(a.id());
        out.println("Devuelto «" + p.get("titulo") + "» (lo tenía " + p.get("persona") + ")"
                + (Boolean.TRUE.equals(p.get("vencido")) ? ", con retraso." : "."));
    }

    private void prestamos(ClienteApi api, Argumentos a) throws IOException {
        a.soloOpciones("vencidos");
        a.sinPosicionales(0);
        List<Object> lista = api.prestamos(a.marca("vencidos"));
        if (lista.isEmpty()) {
            out.println(a.marca("vencidos") ? "No hay préstamos vencidos." : "No hay préstamos activos.");
            return;
        }
        Tabla tabla = new Tabla("ID", "TÍTULO", "PERSONA", "DESDE", "DEVOLVER ANTES DE", "");
        for (Object o : lista) {
            Map<?, ?> p = (Map<?, ?>) o;
            tabla.fila(p.get("libroId"), p.get("titulo"), p.get("persona"), p.get("fecha"),
                    p.get("devolverAntesDe"), Boolean.TRUE.equals(p.get("vencido")) ? "VENCIDO" : "");
        }
        tabla.imprimir(out);
    }

    private void estadisticas(ClienteApi api, Argumentos a) throws IOException {
        a.soloOpciones();
        a.sinPosicionales(0);
        Map<String, Object> e = api.estadisticas();
        out.println("Libros: " + e.get("libros") + "  (disponibles: " + e.get("disponibles")
                + ", prestados: " + e.get("prestados") + ", vencidos: " + e.get("vencidos") + ")");
        if (e.get("porAutor") instanceof List<?> autores && !autores.isEmpty()) {
            out.println();
            out.println("Por autor:");
            for (Object o : autores) {
                Map<?, ?> fila = (Map<?, ?>) o;
                int n = ((Number) fila.get("libros")).intValue();
                out.printf("  %-30s %s %d%n", Tabla.recortar(String.valueOf(fila.get("autor")), 30),
                        "█".repeat(Math.min(n, 40)), n);
            }
        }
        if (e.get("porDecada") instanceof Map<?, ?> decadas && !decadas.isEmpty()) {
            out.println();
            out.println("Por década:");
            decadas.forEach((decada, n) -> out.printf("  %-6s %s %s%n", decada,
                    "█".repeat(Math.min(((Number) n).intValue(), 40)), n));
        }
    }

    private void salud(ClienteApi api, Argumentos a) throws IOException {
        a.soloOpciones();
        a.sinPosicionales(0);
        Map<String, Object> s = api.salud();
        out.println("Servidor " + s.get("estado") + ": " + s.get("libros") + " libros, "
                + s.get("prestamos") + " préstamos activos.");
    }

    private void imprimirLibro(Map<?, ?> l) {
        out.println("  [" + l.get("id") + "] " + l.get("titulo"));
        out.println("  Autor:  " + l.get("autor"));
        out.println("  Año:    " + l.get("anio"));
        Object isbn = l.get("isbn");
        if (isbn instanceof String s && !s.isEmpty()) {
            out.println("  ISBN:   " + s);
        }
        out.println("  Estado: " + (Boolean.TRUE.equals(l.get("disponible")) ? "disponible" : "prestado"));
    }
}
