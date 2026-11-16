package biblioteca.api;

import biblioteca.datos.RepositorioLibros;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Envuelve el servidor HTTP que trae el propio JDK y registra las rutas de la API. */
public class Servidor {

    private final HttpServer http;
    private final ExecutorService hilos = Executors.newFixedThreadPool(4);

    /** Con puerto 0 el sistema elige un puerto libre (lo usan los tests). */
    public Servidor(int puerto, RepositorioLibros repositorio) throws IOException {
        http = HttpServer.create(new InetSocketAddress(puerto), 0);
        http.createContext("/api/libros", new LibrosHandler(repositorio));
        http.createContext("/api/salud", new SaludHandler(repositorio));
        // Cualquier otra ruta: 404 en JSON
        http.createContext("/", intercambio ->
                Respuestas.error(intercambio, 404, "Ruta no encontrada: " + intercambio.getRequestURI().getPath()));
        http.setExecutor(hilos);
    }

    public void arrancar() {
        http.start();
    }

    public void parar() {
        http.stop(0);
        hilos.shutdownNow(); // sin esto los hilos del pool mantienen viva la JVM
    }

    /** Puerto real en el que escucha. */
    public int puerto() {
        return http.getAddress().getPort();
    }
}
