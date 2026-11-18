package biblioteca;

import biblioteca.api.Servidor;
import biblioteca.cliente.ClienteApi;
import biblioteca.cliente.ClienteCli;
import biblioteca.datos.ConflictoException;
import biblioteca.datos.NoEncontradoException;
import biblioteca.datos.RepositorioLibros;
import biblioteca.json.Json;
import biblioteca.json.JsonException;
import biblioteca.modelo.Libro;
import biblioteca.modelo.Prestamo;
import biblioteca.modelo.ValidacionException;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * Tests sin JUnit: un mini "runner" casero para no depender de Maven ni de librerías.
 * Cada prueba es un bloque de código; si lanza una excepción, la prueba falla.
 */
public class Pruebas {

    /** Una prueba es código que puede lanzar cualquier excepción. */
    interface Prueba {
        void ejecutar() throws Exception;
    }

    private static int pasadas = 0;
    private static int falladas = 0;

    public static void main(String[] args) throws Exception {
        pruebasJson();
        pruebasModeloYRepositorio();
        pruebasApi();
        pruebasCrudYPrestamos();
        pruebasApiDia2();
        pruebasDia3();

        System.out.println();
        System.out.println(pasadas + " pruebas pasadas, " + falladas + " falladas");
        if (falladas > 0) {
            System.exit(1);
        }
    }

    // ---------------------------------------------------------------
    // JSON
    // ---------------------------------------------------------------

    @SuppressWarnings("unchecked")
    private static void pruebasJson() {
        prueba("json: lee un objeto con todos los tipos", () -> {
            Map<String, Object> m = (Map<String, Object>) Json.leer(
                    " {\"a\": 1, \"b\": -2.5, \"c\": \"hola\", \"d\": true, \"e\": null, \"f\": [1, [2], {}]} ");
            igual(1L, m.get("a"));
            igual(-2.5, m.get("b"));
            igual("hola", m.get("c"));
            igual(true, m.get("d"));
            igual(null, m.get("e"));
            igual(3, ((List<Object>) m.get("f")).size());
        });
        prueba("json: escapes al leer", () ->
                igual("lí\"nea\n\tñ", Json.leer("\"l\\u00ed\\\"nea\\n\\t\\u00f1\"")));
        prueba("json: escribir y volver a leer da lo mismo", () -> {
            Map<String, Object> original = new LinkedHashMap<>();
            original.put("titulo", "Comillas \" barra \\ salto\n y eñe");
            original.put("anio", 1999L);
            original.put("lista", List.of(1L, "dos", false));
            igual(original, Json.leer(Json.escribir(original)));
        });
        prueba("json: escribe en el orden de inserción", () -> {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id", 1);
            m.put("ok", true);
            igual("{\"id\":1,\"ok\":true}", Json.escribir(m));
        });
        for (String malo : new String[] {"", "{", "{\"a\" 1}", "[1,]", "\"sin cerrar", "tru", "{} extra", "1.2.3"}) {
            prueba("json: rechaza «" + malo + "»", () -> debeLanzar(JsonException.class, () -> Json.leer(malo)));
        }
    }

    // ---------------------------------------------------------------
    // Modelo y repositorio
    // ---------------------------------------------------------------

    private static void pruebasModeloYRepositorio() {
        prueba("libro: recorta espacios", () -> {
            Libro libro = new Libro(1, "  Dune ", " Frank Herbert", 1965, null, true);
            igual("Dune", libro.titulo());
            igual("Frank Herbert", libro.autor());
            igual("", libro.isbn());
        });
        prueba("libro: título vacío no vale", () ->
                debeLanzar(ValidacionException.class, () -> new Libro(1, "  ", "Autor", 2000, "", true)));
        prueba("libro: año fuera de rango no vale", () ->
                debeLanzar(ValidacionException.class, () -> new Libro(1, "T", "A", 3000, "", true)));
        prueba("libro: desdeMapa exige tipos correctos", () -> {
            Map<String, Object> datos = new LinkedHashMap<>();
            datos.put("titulo", "T");
            datos.put("autor", "A");
            datos.put("anio", "mil novecientos");
            debeLanzar(ValidacionException.class, () -> Libro.desdeMapa(1, datos));
            datos.put("anio", 99999999999L); // no cabe en un int: no debe "dar la vuelta"
            debeLanzar(ValidacionException.class, () -> Libro.desdeMapa(1, datos));
            datos.put("anio", 1984L);
            igual(1984, Libro.desdeMapa(1, datos).anio());
        });
        prueba("repositorio: asigna ids consecutivos", () -> {
            RepositorioLibros repo = new RepositorioLibros();
            igual(1, repo.crear("A", "Autor", 2000, "").id());
            igual(2, repo.crear("B", "Autor", 2001, "").id());
            igual(2, repo.total());
            igual("B", repo.buscarPorId(2).orElseThrow().titulo());
            igual(true, repo.buscarPorId(99).isEmpty());
        });
        prueba("repositorio: un libro inválido no gasta id", () -> {
            RepositorioLibros repo = new RepositorioLibros();
            debeLanzar(ValidacionException.class, () -> repo.crear("", "Autor", 2000, ""));
            igual(1, repo.crear("A", "Autor", 2000, "").id());
        });
        prueba("repositorio: guarda en disco y recarga", () -> {
            Path carpeta = Files.createTempDirectory("biblioteca-test");
            Path fichero = carpeta.resolve("sub").resolve("datos.json");
            try {
                RepositorioLibros repo = new RepositorioLibros(fichero);
                repo.crear("El Aleph", "Jorge Luis Borges", 1949, "x-1");
                repo.crear("Ficciones \"anotadas\"", "Borges", 1944, "");

                RepositorioLibros recargado = new RepositorioLibros(fichero);
                igual(repo.listar(), recargado.listar());
                // El contador de ids continúa donde se quedó
                igual(3, recargado.crear("Otro", "Autor", 2000, "").id());
            } finally {
                Files.deleteIfExists(fichero);
                Files.deleteIfExists(fichero.getParent());
                Files.deleteIfExists(carpeta);
            }
        });
    }

    // ---------------------------------------------------------------
    // API HTTP (tests de integración: servidor real en un puerto libre)
    // ---------------------------------------------------------------

    @SuppressWarnings("unchecked")
    private static void pruebasApi() throws Exception {
        RepositorioLibros repo = new RepositorioLibros();
        repo.crear("Don Quijote", "Cervantes", 1605, "");
        Servidor servidor = new Servidor(0, repo);
        servidor.arrancar();
        String base = "http://localhost:" + servidor.puerto();
        HttpClient cliente = HttpClient.newHttpClient();
        try {
            prueba("api: GET /api/salud", () -> {
                HttpResponse<String> r = pedir(cliente, "GET", base + "/api/salud", null);
                igual(200, r.statusCode());
                igual("ok", ((Map<String, Object>) Json.leer(r.body())).get("estado"));
            });
            prueba("api: GET /api/libros devuelve la lista en JSON", () -> {
                HttpResponse<String> r = pedir(cliente, "GET", base + "/api/libros", null);
                igual(200, r.statusCode());
                igual("application/json; charset=utf-8", r.headers().firstValue("Content-Type").orElse(""));
                List<Object> lista = (List<Object>) Json.leer(r.body());
                igual("Don Quijote", ((Map<String, Object>) lista.get(0)).get("titulo"));
            });
            prueba("api: POST crea un libro y luego se puede consultar", () -> {
                HttpResponse<String> r = pedir(cliente, "POST", base + "/api/libros",
                        "{\"titulo\":\"La colmena\",\"autor\":\"Camilo José Cela\",\"anio\":1951}");
                igual(201, r.statusCode());
                Map<String, Object> creado = (Map<String, Object>) Json.leer(r.body());
                igual(2L, creado.get("id"));
                igual(true, creado.get("disponible"));
                igual("/api/libros/2", r.headers().firstValue("Location").orElse(""));

                HttpResponse<String> consulta = pedir(cliente, "GET", base + "/api/libros/2", null);
                igual(200, consulta.statusCode());
                igual("Camilo José Cela", ((Map<String, Object>) Json.leer(consulta.body())).get("autor"));
            });
            prueba("api: POST con JSON roto -> 400", () ->
                    igual(400, pedir(cliente, "POST", base + "/api/libros", "{\"titulo\":").statusCode()));
            prueba("api: POST sin título -> 400 con mensaje", () -> {
                HttpResponse<String> r = pedir(cliente, "POST", base + "/api/libros", "{\"autor\":\"X\",\"anio\":2000}");
                igual(400, r.statusCode());
                igual("Falta el campo 'titulo'", ((Map<String, Object>) Json.leer(r.body())).get("error"));
            });
            prueba("api: POST con un array -> 400", () ->
                    igual(400, pedir(cliente, "POST", base + "/api/libros", "[1,2]").statusCode()));
            prueba("api: libro inexistente -> 404", () ->
                    igual(404, pedir(cliente, "GET", base + "/api/libros/999", null).statusCode()));
            prueba("api: id no numérico -> 400", () ->
                    igual(400, pedir(cliente, "GET", base + "/api/libros/abc", null).statusCode()));
            prueba("api: método no soportado -> 405", () ->
                    igual(405, pedir(cliente, "DELETE", base + "/api/libros", null).statusCode()));
            prueba("api: ruta desconocida -> 404", () -> {
                igual(404, pedir(cliente, "GET", base + "/nada", null).statusCode());
                igual(404, pedir(cliente, "GET", base + "/api/libros/1/extra", null).statusCode());
                igual(404, pedir(cliente, "GET", base + "/api/librosXYZ", null).statusCode());
            });
        } finally {
            servidor.parar();
        }
    }

    // ---------------------------------------------------------------
    // Día 2: CRUD completo, búsqueda y préstamos (repositorio)
    // ---------------------------------------------------------------

    /** Reloj fijo para que las fechas de los préstamos sean siempre las mismas. */
    private static Clock relojFijo(String fecha) {
        return Clock.fixed(Instant.parse(fecha + "T10:00:00Z"), ZoneOffset.UTC);
    }

    private static Map<String, Object> datosLibro(String titulo, String autor, long anio) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("titulo", titulo);
        m.put("autor", autor);
        m.put("anio", anio);
        return m;
    }

    private static RepositorioLibros repoDeEjemplo(Clock reloj) {
        RepositorioLibros repo = new RepositorioLibros(null, reloj);
        repo.crear("Cien años de soledad", "Gabriel García Márquez", 1967, "978-84-376-0495-4");
        repo.crear("El amor en los tiempos del cólera", "Gabriel García Márquez", 1985, "");
        repo.crear("Rayuela", "Julio Cortázar", 1963, "");
        return repo;
    }

    private static void pruebasCrudYPrestamos() {
        Clock reloj = relojFijo("2026-11-17");
        prueba("buscar: sin criterios devuelve todo", () ->
                igual(3, repoDeEjemplo(reloj).buscar(null, null, null).size()));
        prueba("buscar: ignora mayúsculas y tildes", () -> {
            RepositorioLibros repo = repoDeEjemplo(reloj);
            igual(2, repo.buscar("MARQUEZ", null, null).size());
            igual(1, repo.buscar("colera", null, null).size());
            igual(1, repo.buscar(null, "cortazar", null).size());
            igual(0, repo.buscar("tolkien", null, null).size());
            igual(1, repo.buscar("0495", null, null).size()); // también busca en el ISBN
        });
        prueba("actualizar: cambia datos y conserva la disponibilidad", () -> {
            RepositorioLibros repo = repoDeEjemplo(reloj);
            repo.prestar(3, "Ana", 7);
            Libro nuevo = repo.actualizar(3, datosLibro("Rayuela (ed. 2013)", "Julio Cortázar", 2013));
            igual("Rayuela (ed. 2013)", nuevo.titulo());
            igual(false, nuevo.disponible());
        });
        prueba("actualizar/borrar: id inexistente -> NoEncontrado", () -> {
            RepositorioLibros repo = repoDeEjemplo(reloj);
            debeLanzar(NoEncontradoException.class, () -> repo.actualizar(99, datosLibro("T", "A", 2000)));
            debeLanzar(NoEncontradoException.class, () -> repo.borrar(99));
        });
        prueba("actualizar: datos inválidos no cambian nada", () -> {
            RepositorioLibros repo = repoDeEjemplo(reloj);
            debeLanzar(ValidacionException.class, () -> repo.actualizar(1, datosLibro("", "A", 2000)));
            igual("Cien años de soledad", repo.buscarPorId(1).orElseThrow().titulo());
        });
        prueba("borrar: quita el libro y no reutiliza su id", () -> {
            RepositorioLibros repo = repoDeEjemplo(reloj);
            repo.borrar(3);
            igual(2, repo.total());
            igual(4, repo.crear("Nuevo", "Autor", 2020, "").id());
        });
        prueba("préstamo: fechas, disponibilidad y devolución", () -> {
            RepositorioLibros repo = repoDeEjemplo(reloj);
            Prestamo p = repo.prestar(1, "  Lucía ", 14);
            igual("Lucía", p.persona());
            igual(LocalDate.of(2026, 11, 17), p.fecha());
            igual(LocalDate.of(2026, 12, 1), p.devolverAntesDe());
            igual(false, repo.buscarPorId(1).orElseThrow().disponible());
            igual(1, repo.prestamosActivos().size());
            igual(1, repo.buscar(null, null, false).size());
            repo.devolver(1);
            igual(true, repo.buscarPorId(1).orElseThrow().disponible());
            igual(0, repo.prestamosActivos().size());
        });
        prueba("préstamo: reglas (doble préstamo, devolver sin prestar, borrar prestado)", () -> {
            RepositorioLibros repo = repoDeEjemplo(reloj);
            repo.prestar(2, "Ana", 7);
            debeLanzar(ConflictoException.class, () -> repo.prestar(2, "Luis", 7));
            debeLanzar(ConflictoException.class, () -> repo.devolver(1));
            debeLanzar(ConflictoException.class, () -> repo.borrar(2));
            debeLanzar(ValidacionException.class, () -> repo.prestar(1, "  ", 7));
            debeLanzar(ValidacionException.class, () -> repo.prestar(1, "Ana", 0));
            debeLanzar(ValidacionException.class, () -> repo.prestar(1, "Ana", 61));
            debeLanzar(NoEncontradoException.class, () -> repo.prestar(99, "Ana", 7));
            igual(true, repo.buscarPorId(1).orElseThrow().disponible()); // los fallos no cambian nada
        });
        prueba("préstamo: vencido cuando pasa la fecha límite", () -> {
            Prestamo p = new Prestamo(1, "Ana", LocalDate.of(2026, 11, 1), LocalDate.of(2026, 11, 15));
            igual(false, p.vencido(LocalDate.of(2026, 11, 15)));
            igual(true, p.vencido(LocalDate.of(2026, 11, 16)));
        });
        prueba("persistencia: préstamos y borrados sobreviven a un reinicio", () -> {
            Path carpeta = Files.createTempDirectory("biblioteca-test");
            Path fichero = carpeta.resolve("datos.json");
            try {
                RepositorioLibros repo = new RepositorioLibros(fichero, reloj);
                repo.crear("A", "Autor", 2000, "");
                repo.crear("B", "Autor", 2001, "");
                repo.crear("C", "Autor", 2002, "");
                repo.borrar(3);
                repo.prestar(2, "Marta", 10);

                RepositorioLibros recargado = new RepositorioLibros(fichero, reloj);
                igual(repo.listar(), recargado.listar());
                igual(repo.prestamosActivos(), recargado.prestamosActivos());
                igual(4, recargado.crear("D", "Autor", 2003, "").id()); // el 3 no se reutiliza
            } finally {
                Files.deleteIfExists(fichero);
                Files.deleteIfExists(carpeta);
            }
        });
    }

    // ---------------------------------------------------------------
    // Día 2: API HTTP de PUT, DELETE, filtros y préstamos
    // ---------------------------------------------------------------

    @SuppressWarnings("unchecked")
    private static void pruebasApiDia2() throws Exception {
        // Reloj fijo: así sabemos exactamente qué fechas devolverá la API
        RepositorioLibros repo = repoDeEjemplo(relojFijo("2026-11-17"));
        Servidor servidor = new Servidor(0, repo);
        servidor.arrancar();
        String base = "http://localhost:" + servidor.puerto();
        HttpClient cliente = HttpClient.newHttpClient();
        try {
            prueba("api: filtros ?q=, ?autor= y ?disponible=", () -> {
                igual(2, ((List<Object>) Json.leer(pedir(cliente, "GET",
                        base + "/api/libros?q=garc%C3%ADa", null).body())).size());
                igual(1, ((List<Object>) Json.leer(pedir(cliente, "GET",
                        base + "/api/libros?autor=Cort%C3%A1zar&disponible=true", null).body())).size());
                igual(0, ((List<Object>) Json.leer(pedir(cliente, "GET",
                        base + "/api/libros?disponible=false", null).body())).size());
            });
            prueba("api: filtros incorrectos -> 400", () -> {
                igual(400, pedir(cliente, "GET", base + "/api/libros?disponible=quizas", null).statusCode());
                igual(400, pedir(cliente, "GET", base + "/api/libros?color=rojo", null).statusCode());
            });
            prueba("api: PUT actualiza", () -> {
                HttpResponse<String> r = pedir(cliente, "PUT", base + "/api/libros/3",
                        "{\"titulo\":\"Rayuela\",\"autor\":\"Julio Cortázar\",\"anio\":1963,\"isbn\":\"978-84-376-0474-9\"}");
                igual(200, r.statusCode());
                igual("978-84-376-0474-9", ((Map<String, Object>) Json.leer(r.body())).get("isbn"));
            });
            prueba("api: PUT con datos inválidos -> 400 y con id inexistente -> 404", () -> {
                igual(400, pedir(cliente, "PUT", base + "/api/libros/3", "{\"titulo\":\"X\"}").statusCode());
                igual(404, pedir(cliente, "PUT", base + "/api/libros/99",
                        "{\"titulo\":\"X\",\"autor\":\"Y\",\"anio\":2000}").statusCode());
            });
            prueba("api: prestar -> 201 con fechas y título", () -> {
                HttpResponse<String> r = pedir(cliente, "POST", base + "/api/libros/1/prestamo",
                        "{\"persona\":\"Lucía\",\"dias\":7}");
                igual(201, r.statusCode());
                Map<String, Object> p = (Map<String, Object>) Json.leer(r.body());
                igual("Lucía", p.get("persona"));
                igual("2026-11-24", p.get("devolverAntesDe"));
                igual("Cien años de soledad", p.get("titulo"));
                igual(false, p.get("vencido"));
            });
            prueba("api: prestar de nuevo -> 409, sin persona -> 400", () -> {
                HttpResponse<String> r = pedir(cliente, "POST", base + "/api/libros/1/prestamo", "{\"persona\":\"Luis\"}");
                igual(409, r.statusCode());
                igual("El libro 1 no está disponible", ((Map<String, Object>) Json.leer(r.body())).get("error"));
                igual(400, pedir(cliente, "POST", base + "/api/libros/2/prestamo", "{}").statusCode());
                igual(400, pedir(cliente, "POST", base + "/api/libros/2/prestamo",
                        "{\"persona\":\"Luis\",\"dias\":\"muchos\"}").statusCode());
                igual(400, pedir(cliente, "POST", base + "/api/libros/2/prestamo",
                        "{\"persona\":\"Luis\",\"dias\":99999999999}").statusCode());
            });
            prueba("api: GET /api/prestamos lista los activos", () -> {
                HttpResponse<String> r = pedir(cliente, "GET", base + "/api/prestamos", null);
                igual(200, r.statusCode());
                List<Object> lista = (List<Object>) Json.leer(r.body());
                igual(1, lista.size());
                igual(1L, ((Map<String, Object>) lista.get(0)).get("libroId"));
                igual(0, ((List<Object>) Json.leer(pedir(cliente, "GET",
                        base + "/api/prestamos?vencidos=true", null).body())).size());
                igual(405, pedir(cliente, "POST", base + "/api/prestamos", "{}").statusCode());
            });
            prueba("api: DELETE de un libro prestado -> 409", () ->
                    igual(409, pedir(cliente, "DELETE", base + "/api/libros/1", null).statusCode()));
            prueba("api: devolver -> 200 y devolver otra vez -> 409", () -> {
                igual(200, pedir(cliente, "DELETE", base + "/api/libros/1/prestamo", null).statusCode());
                igual(409, pedir(cliente, "DELETE", base + "/api/libros/1/prestamo", null).statusCode());
                igual(true, repo.buscarPorId(1).orElseThrow().disponible());
            });
            prueba("api: DELETE borra -> 204 y después 404", () -> {
                HttpResponse<String> r = pedir(cliente, "DELETE", base + "/api/libros/2", null);
                igual(204, r.statusCode());
                igual("", r.body());
                igual(404, pedir(cliente, "GET", base + "/api/libros/2", null).statusCode());
                igual(404, pedir(cliente, "DELETE", base + "/api/libros/2", null).statusCode());
            });
            prueba("api: 405 incluye la cabecera Allow", () -> {
                HttpResponse<String> r = pedir(cliente, "PATCH", base + "/api/libros/1", "{}");
                igual(405, r.statusCode());
                igual("GET, PUT, DELETE", r.headers().firstValue("Allow").orElse(""));
            });
        } finally {
            servidor.parar();
        }
    }

    // ---------------------------------------------------------------
    // Día 3: estadísticas, ClienteApi y cliente de terminal
    // ---------------------------------------------------------------

    /** Resultado de ejecutar el CLI: código de salida y lo que ha escrito. */
    record Salida(int codigo, String out, String err) {
    }

    private static Salida cli(String base, String... args) {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        ByteArrayOutputStream err = new ByteArrayOutputStream();
        String[] completos = new String[args.length + 2];
        completos[0] = "--url";
        completos[1] = base;
        System.arraycopy(args, 0, completos, 2, args.length);
        int codigo = new ClienteCli(new PrintStream(out, true, StandardCharsets.UTF_8),
                new PrintStream(err, true, StandardCharsets.UTF_8)).ejecutar(completos);
        return new Salida(codigo, out.toString(StandardCharsets.UTF_8), err.toString(StandardCharsets.UTF_8));
    }

    private static void contiene(String texto, String trozo) {
        if (!texto.contains(trozo)) {
            throw new AssertionError("se esperaba que contuviera «" + trozo + "» pero era:\n" + texto);
        }
    }

    @SuppressWarnings("unchecked")
    private static void pruebasDia3() throws Exception {
        // Preparamos un préstamo vencido: se presta el 1 de noviembre a 7 días y se
        // recarga el fichero con el reloj a 17 de noviembre.
        Path carpeta = Files.createTempDirectory("biblioteca-dia3");
        Path fichero = carpeta.resolve("datos.json");
        RepositorioLibros antes = new RepositorioLibros(fichero, relojFijo("2026-11-01"));
        antes.crear("Cien años de soledad", "Gabriel García Márquez", 1967, "978-84-376-0495-4");
        antes.crear("El amor en los tiempos del cólera", "Gabriel García Márquez", 1985, "");
        antes.crear("Rayuela", "Julio Cortázar", 1963, "");
        antes.prestar(3, "Pablo", 7);
        RepositorioLibros repo = new RepositorioLibros(fichero, relojFijo("2026-11-17"));

        Servidor servidor = new Servidor(0, repo);
        servidor.arrancar();
        String base = "http://localhost:" + servidor.puerto();
        HttpClient http = HttpClient.newHttpClient();
        ClienteApi api = new ClienteApi(base + "/"); // la barra final no debe molestar
        try {
            prueba("api: GET /api/estadisticas", () -> {
                HttpResponse<String> r = pedir(http, "GET", base + "/api/estadisticas", null);
                igual(200, r.statusCode());
                Map<String, Object> e = (Map<String, Object>) Json.leer(r.body());
                igual(3L, e.get("libros"));
                igual(2L, e.get("disponibles"));
                igual(1L, e.get("prestados"));
                igual(1L, e.get("vencidos"));
                Map<String, Object> primero = (Map<String, Object>) ((List<Object>) e.get("porAutor")).get(0);
                igual("Gabriel García Márquez", primero.get("autor"));
                igual(2L, primero.get("libros"));
                igual(List.of("1960s", "1980s"),
                        List.copyOf(((Map<String, Object>) e.get("porDecada")).keySet()));
                igual(405, pedir(http, "POST", base + "/api/estadisticas", "{}").statusCode());
            });
            prueba("api: /api/salud con método incorrecto -> 405 con Allow", () -> {
                HttpResponse<String> r = pedir(http, "POST", base + "/api/salud", "{}");
                igual(405, r.statusCode());
                igual("GET", r.headers().firstValue("Allow").orElse(""));
            });
            prueba("ClienteApi: listar con filtros codifica tildes y espacios", () -> {
                igual(2, api.listar("garcía márquez", null, null).size());
                igual(1, api.listar(null, "Cortázar", false).size());
                igual(3, api.listar("", null, null).size()); // vacío = sin filtro
            });
            prueba("ClienteApi: los errores llevan código y mensaje de la API", () -> {
                try {
                    api.ver(99);
                    throw new AssertionError("debía fallar");
                } catch (ClienteApi.ErrorApi e) {
                    igual(404, e.estado());
                    igual("No existe el libro con id 99", e.getMessage());
                }
            });
            prueba("ClienteApi: servidor apagado -> IOException (no se cuelga)", () ->
                    debeLanzar(java.io.IOException.class, () -> new ClienteApi("http://localhost:1").salud()));

            prueba("cli: sin argumentos muestra la ayuda y sale con 2", () -> {
                Salida s = cli(base);
                igual(2, s.codigo());
                contiene(s.out(), "Comandos:");
            });
            prueba("cli: listar pinta una tabla", () -> {
                Salida s = cli(base, "listar");
                igual(0, s.codigo());
                contiene(s.out(), "TÍTULO");
                contiene(s.out(), "Rayuela");
                contiene(s.out(), "3 libros");
            });
            prueba("cli: listar --prestados y --buscar", () -> {
                Salida s = cli(base, "listar", "--prestados");
                contiene(s.out(), "1 libro");
                contiene(s.out(), "Rayuela");
                igual("No hay libros que coincidan.\n", cli(base, "listar", "--buscar", "tolkien").out());
            });
            prueba("cli: crear y ver", () -> {
                Salida s = cli(base, "crear", "--titulo", "Ficciones", "--autor", "Jorge Luis Borges",
                        "--anio=1944");
                igual(0, s.codigo());
                contiene(s.out(), "Libro creado con id 4");
                contiene(cli(base, "ver", "4").out(), "Jorge Luis Borges");
            });
            prueba("cli: crear sin campos obligatorios -> 2 sin llamar a la API", () -> {
                Salida s = cli(base, "crear", "--titulo", "Sin autor", "--anio", "2000");
                igual(2, s.codigo());
                contiene(s.err(), "Falta --autor");
                igual(2, cli(base, "crear", "--titulo", "T", "--autor", "A", "--anio", "dos mil").codigo());
                igual(4, repo.total());
            });
            prueba("cli: editar cambia solo los campos indicados", () -> {
                igual(0, cli(base, "editar", "4", "--anio", "1956").codigo());
                Libro libro = repo.buscarPorId(4).orElseThrow();
                igual(1956, libro.anio());
                igual("Ficciones", libro.titulo());
                igual(2, cli(base, "editar", "4").codigo()); // sin campos: uso incorrecto
            });
            prueba("cli: prestar, ver quién lo tiene y devolver", () -> {
                Salida s = cli(base, "prestar", "4", "Ana López", "--dias", "10");
                igual(0, s.codigo());
                contiene(s.out(), "Devolver antes del 2026-11-27");
                contiene(cli(base, "ver", "4").out(), "Prestado a: Ana López");
                contiene(cli(base, "devolver", "4").out(), "Devuelto «Ficciones»");
            });
            prueba("cli: prestamos --vencidos marca el retraso", () -> {
                Salida s = cli(base, "prestamos", "--vencidos");
                contiene(s.out(), "Pablo");
                contiene(s.out(), "VENCIDO");
                contiene(cli(base, "devolver", "3").out(), "con retraso");
                igual("No hay préstamos activos.\n", cli(base, "prestamos").out());
            });
            prueba("cli: errores de la API -> código 1 y mensaje", () -> {
                Salida s = cli(base, "ver", "99");
                igual(1, s.codigo());
                contiene(s.err(), "Error 404");
                igual(1, cli(base, "devolver", "1").codigo()); // no estaba prestado: 409
            });
            prueba("cli: argumentos incorrectos -> código 2", () -> {
                igual(2, cli(base, "ver", "abc").codigo());
                igual(2, cli(base, "ver").codigo());
                igual(2, cli(base, "ver", "1", "2").codigo());
                igual(2, cli(base, "listar", "--disponibles", "--prestados").codigo());
                igual(2, cli(base, "listar", "--color", "rojo").codigo());
                igual(2, cli(base, "prestar", "1").codigo());
                igual(2, cli(base, "volar").codigo());
            });
            prueba("cli: borrar y estadísticas", () -> {
                igual(0, cli(base, "borrar", "4").codigo());
                Salida s = cli(base, "estadisticas");
                contiene(s.out(), "Libros: 3");
                contiene(s.out(), "Gabriel García Márquez");
                contiene(s.out(), "1980s");
            });
            prueba("cli: servidor apagado -> mensaje claro y código 1", () -> {
                Salida s = cli("http://localhost:1", "salud");
                igual(1, s.codigo());
                contiene(s.err(), "No se puede conectar");
            });
        } finally {
            servidor.parar();
            Files.deleteIfExists(fichero);
            Files.deleteIfExists(carpeta);
        }
    }

    private static HttpResponse<String> pedir(HttpClient cliente, String metodo, String url, String cuerpo)
            throws Exception {
        HttpRequest.BodyPublisher publicador = cuerpo == null
                ? HttpRequest.BodyPublishers.noBody()
                : HttpRequest.BodyPublishers.ofString(cuerpo);
        HttpRequest peticion = HttpRequest.newBuilder(URI.create(url)).method(metodo, publicador).build();
        return cliente.send(peticion, HttpResponse.BodyHandlers.ofString());
    }

    // ---------------------------------------------------------------
    // Mini runner
    // ---------------------------------------------------------------

    private static void prueba(String nombre, Prueba codigo) {
        try {
            codigo.ejecutar();
            pasadas++;
            System.out.println("  OK    " + nombre);
        } catch (Throwable e) {
            falladas++;
            System.out.println("  FALLO " + nombre + " -> " + e);
        }
    }

    private static void igual(Object esperado, Object obtenido) {
        if (!Objects.equals(esperado, obtenido)) {
            throw new AssertionError("se esperaba <" + esperado + "> pero se obtuvo <" + obtenido + ">");
        }
    }

    private static void debeLanzar(Class<? extends Throwable> tipo, Prueba codigo) {
        try {
            codigo.ejecutar();
        } catch (Throwable e) {
            if (tipo.isInstance(e)) {
                return;
            }
            throw new AssertionError("se esperaba " + tipo.getSimpleName() + " pero se lanzó " + e);
        }
        throw new AssertionError("se esperaba " + tipo.getSimpleName() + " y no se lanzó nada");
    }
}
