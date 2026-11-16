package biblioteca;

import biblioteca.api.Servidor;
import biblioteca.datos.RepositorioLibros;

import java.io.IOException;
import java.nio.file.Path;

/**
 * Punto de entrada: arranca la API de la biblioteca.
 *
 * Uso: java -cp out biblioteca.Main [--puerto 8080] [--datos datos/biblioteca.json]
 */
public class Main {

    public static void main(String[] args) throws IOException {
        int puerto = 8080;
        Path datos = Path.of("datos", "biblioteca.json");

        // Lectura sencilla de argumentos "--nombre valor"
        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--puerto" -> puerto = leerPuerto(valorDe(args, ++i, "--puerto"));
                case "--datos" -> datos = Path.of(valorDe(args, ++i, "--datos"));
                case "--ayuda", "-h" -> {
                    System.out.println("Uso: biblioteca.Main [--puerto N] [--datos fichero.json]");
                    return;
                }
                default -> salirConError("Argumento desconocido: " + args[i]);
            }
        }

        RepositorioLibros repositorio = new RepositorioLibros(datos);
        if (repositorio.total() == 0) {
            sembrarEjemplos(repositorio);
        }

        Servidor servidor = new Servidor(puerto, repositorio);
        servidor.arrancar();
        System.out.println("Biblioteca API escuchando en http://localhost:" + servidor.puerto());
        System.out.println("Datos en: " + datos.toAbsolutePath());
        System.out.println("Prueba:   curl http://localhost:" + servidor.puerto() + "/api/libros");
        System.out.println("Ctrl+C para parar.");
    }

    /** Unos cuantos libros para que la API no esté vacía la primera vez. */
    private static void sembrarEjemplos(RepositorioLibros repositorio) {
        repositorio.crear("Don Quijote de la Mancha", "Miguel de Cervantes", 1605, "978-84-376-0494-7");
        repositorio.crear("Cien años de soledad", "Gabriel García Márquez", 1967, "978-84-376-0495-4");
        repositorio.crear("Clean Code", "Robert C. Martin", 2008, "978-0-13-235088-4");
    }

    private static String valorDe(String[] args, int indice, String opcion) {
        if (indice >= args.length) {
            salirConError("Falta el valor de " + opcion);
        }
        return args[indice];
    }

    private static int leerPuerto(String texto) {
        try {
            int puerto = Integer.parseInt(texto);
            if (puerto >= 0 && puerto <= 65535) {
                return puerto;
            }
        } catch (NumberFormatException e) {
            // se trata abajo
        }
        salirConError("Puerto no válido: " + texto);
        return -1; // inalcanzable
    }

    private static void salirConError(String mensaje) {
        System.err.println(mensaje);
        System.exit(2);
    }
}
