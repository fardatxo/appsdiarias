package biblioteca;

import biblioteca.api.Servidor;
import biblioteca.datos.RepositorioLibros;
import biblioteca.json.Json;
import biblioteca.json.JsonException;
import biblioteca.modelo.Libro;
import biblioteca.modelo.ValidacionException;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
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
