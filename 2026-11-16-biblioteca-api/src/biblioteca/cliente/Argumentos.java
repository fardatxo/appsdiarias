package biblioteca.cliente;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Lector de argumentos del cliente: separa posicionales ("3", "Ana"),
 * opciones con valor ("--autor Borges" o "--autor=Borges") y marcas sin valor ("--vencidos").
 * Los errores se lanzan como IllegalArgumentException (el CLI los muestra como "uso incorrecto").
 */
final class Argumentos {

    /** Opciones que no llevan valor detrás. */
    private static final Set<String> MARCAS = Set.of("disponibles", "prestados", "vencidos");

    private final List<String> posicionales = new ArrayList<>();
    private final Map<String, String> opciones = new LinkedHashMap<>();

    private Argumentos() {
    }

    static Argumentos leer(List<String> args) {
        Argumentos a = new Argumentos();
        for (int i = 0; i < args.size(); i++) {
            String arg = args.get(i);
            if (!arg.startsWith("--") || arg.length() == 2) {
                a.posicionales.add(arg);
                continue;
            }
            String nombre = arg.substring(2);
            String valor;
            int igual = nombre.indexOf('=');
            if (igual >= 0) {
                valor = nombre.substring(igual + 1);
                nombre = nombre.substring(0, igual);
            } else if (MARCAS.contains(nombre)) {
                valor = "true";
            } else if (i + 1 < args.size()) {
                valor = args.get(++i);
            } else {
                throw new IllegalArgumentException("Falta el valor de --" + nombre);
            }
            if (a.opciones.put(nombre, valor) != null) {
                throw new IllegalArgumentException("La opción --" + nombre + " está repetida");
            }
        }
        return a;
    }

    List<String> posicionales() {
        return posicionales;
    }

    /** Valor de una opción o null si no se ha indicado. */
    String opcion(String nombre) {
        return opciones.get(nombre);
    }

    boolean marca(String nombre) {
        return opciones.containsKey(nombre);
    }

    String obligatoria(String nombre) {
        String valor = opciones.get(nombre);
        if (valor == null || valor.isBlank()) {
            throw new IllegalArgumentException("Falta --" + nombre);
        }
        return valor;
    }

    /** Lee una opción numérica; si es obligatoria y no está, error. */
    Integer entero(String nombre, boolean obligatoria) {
        String valor = obligatoria ? obligatoria(nombre) : opciones.get(nombre);
        if (valor == null) {
            return null;
        }
        try {
            return Integer.parseInt(valor.trim());
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("--" + nombre + " debe ser un número entero: " + valor);
        }
    }

    /** Comprueba que no se ha pasado ninguna opción distinta de las permitidas. */
    void soloOpciones(String... permitidas) {
        Set<String> validas = Set.of(permitidas);
        for (String nombre : opciones.keySet()) {
            if (!validas.contains(nombre)) {
                throw new IllegalArgumentException("Opción desconocida para este comando: --" + nombre);
            }
        }
    }

    /** Comprueba que no sobran posicionales. */
    void sinPosicionales(int maximo) {
        if (posicionales.size() > maximo) {
            throw new IllegalArgumentException("Sobran argumentos: " + posicionales.subList(maximo, posicionales.size()));
        }
    }

    /** Para comandos de la forma "COMANDO ID": exactamente un posicional numérico. */
    int id() {
        if (posicionales.isEmpty()) {
            throw new IllegalArgumentException("Falta el ID del libro");
        }
        sinPosicionales(1);
        return leerId(posicionales.get(0));
    }

    static int leerId(String texto) {
        try {
            int id = Integer.parseInt(texto);
            if (id > 0) {
                return id;
            }
        } catch (NumberFormatException e) {
            // se trata abajo
        }
        throw new IllegalArgumentException("El ID debe ser un número positivo: " + texto);
    }
}
