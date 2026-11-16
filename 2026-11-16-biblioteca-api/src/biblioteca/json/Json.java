package biblioteca.json;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Mini librería JSON hecha a mano (sin dependencias).
 *
 * Correspondencia entre JSON y Java:
 *   objeto  -> Map<String, Object> (LinkedHashMap, conserva el orden)
 *   array   -> List<Object>
 *   cadena  -> String
 *   número  -> Long (enteros) o Double (decimales)
 *   true/false -> Boolean
 *   null    -> null
 */
public final class Json {

    private Json() {
    }

    // ---------------------------------------------------------------
    // Escritura: de objetos Java a texto JSON
    // ---------------------------------------------------------------

    /** Convierte un valor Java (Map, List, String, Number, Boolean o null) a JSON. */
    public static String escribir(Object valor) {
        StringBuilder sb = new StringBuilder();
        escribirValor(valor, sb);
        return sb.toString();
    }

    private static void escribirValor(Object valor, StringBuilder sb) {
        if (valor == null) {
            sb.append("null");
        } else if (valor instanceof String texto) {
            escribirCadena(texto, sb);
        } else if (valor instanceof Number || valor instanceof Boolean) {
            sb.append(valor);
        } else if (valor instanceof Map<?, ?> mapa) {
            sb.append('{');
            boolean primero = true;
            for (Map.Entry<?, ?> entrada : mapa.entrySet()) {
                if (!primero) {
                    sb.append(',');
                }
                primero = false;
                escribirCadena(String.valueOf(entrada.getKey()), sb);
                sb.append(':');
                escribirValor(entrada.getValue(), sb);
            }
            sb.append('}');
        } else if (valor instanceof Iterable<?> lista) {
            sb.append('[');
            boolean primero = true;
            for (Object elemento : lista) {
                if (!primero) {
                    sb.append(',');
                }
                primero = false;
                escribirValor(elemento, sb);
            }
            sb.append(']');
        } else {
            throw new IllegalArgumentException("Tipo no soportado en JSON: " + valor.getClass());
        }
    }

    /** Escribe una cadena entre comillas escapando los caracteres especiales. */
    private static void escribirCadena(String texto, StringBuilder sb) {
        sb.append('"');
        for (int i = 0; i < texto.length(); i++) {
            char c = texto.charAt(i);
            switch (c) {
                case '"' -> sb.append("\\\"");
                case '\\' -> sb.append("\\\\");
                case '\n' -> sb.append("\\n");
                case '\r' -> sb.append("\\r");
                case '\t' -> sb.append("\\t");
                default -> {
                    if (c < 0x20) {
                        sb.append(String.format("\\u%04x", (int) c));
                    } else {
                        sb.append(c);
                    }
                }
            }
        }
        sb.append('"');
    }

    // ---------------------------------------------------------------
    // Lectura: de texto JSON a objetos Java (parser descendente recursivo)
    // ---------------------------------------------------------------

    /** Analiza un texto JSON completo. Lanza JsonException si está mal formado. */
    public static Object leer(String texto) {
        if (texto == null) {
            throw new JsonException("No hay texto que leer", 0);
        }
        Lector lector = new Lector(texto);
        lector.saltarEspacios();
        Object valor = lector.leerValor();
        lector.saltarEspacios();
        if (!lector.fin()) {
            throw new JsonException("Sobra texto después del valor", lector.pos);
        }
        return valor;
    }

    /** Guarda el texto y la posición por la que vamos leyendo. */
    private static final class Lector {
        private final String texto;
        private int pos = 0;

        Lector(String texto) {
            this.texto = texto;
        }

        boolean fin() {
            return pos >= texto.length();
        }

        void saltarEspacios() {
            while (!fin() && Character.isWhitespace(texto.charAt(pos))) {
                pos++;
            }
        }

        /** Mira el primer carácter y decide qué tipo de valor viene. */
        Object leerValor() {
            if (fin()) {
                throw new JsonException("Se esperaba un valor", pos);
            }
            char c = texto.charAt(pos);
            if (c == '{') {
                return leerObjeto();
            }
            if (c == '[') {
                return leerArray();
            }
            if (c == '"') {
                return leerCadena();
            }
            if (c == '-' || Character.isDigit(c)) {
                return leerNumero();
            }
            if (texto.startsWith("true", pos)) {
                pos += 4;
                return Boolean.TRUE;
            }
            if (texto.startsWith("false", pos)) {
                pos += 5;
                return Boolean.FALSE;
            }
            if (texto.startsWith("null", pos)) {
                pos += 4;
                return null;
            }
            throw new JsonException("Carácter inesperado '" + c + "'", pos);
        }

        Map<String, Object> leerObjeto() {
            Map<String, Object> mapa = new LinkedHashMap<>();
            pos++; // saltamos '{'
            saltarEspacios();
            if (!fin() && texto.charAt(pos) == '}') {
                pos++;
                return mapa;
            }
            while (true) {
                saltarEspacios();
                if (fin() || texto.charAt(pos) != '"') {
                    throw new JsonException("Se esperaba una clave entre comillas", pos);
                }
                String clave = leerCadena();
                saltarEspacios();
                esperar(':');
                saltarEspacios();
                mapa.put(clave, leerValor());
                saltarEspacios();
                if (!fin() && texto.charAt(pos) == ',') {
                    pos++;
                } else {
                    esperar('}');
                    return mapa;
                }
            }
        }

        List<Object> leerArray() {
            List<Object> lista = new ArrayList<>();
            pos++; // saltamos '['
            saltarEspacios();
            if (!fin() && texto.charAt(pos) == ']') {
                pos++;
                return lista;
            }
            while (true) {
                saltarEspacios();
                lista.add(leerValor());
                saltarEspacios();
                if (!fin() && texto.charAt(pos) == ',') {
                    pos++;
                } else {
                    esperar(']');
                    return lista;
                }
            }
        }

        String leerCadena() {
            StringBuilder sb = new StringBuilder();
            pos++; // saltamos la comilla inicial
            while (true) {
                if (fin()) {
                    throw new JsonException("Cadena sin cerrar", pos);
                }
                char c = texto.charAt(pos++);
                if (c == '"') {
                    return sb.toString();
                }
                if (c != '\\') {
                    sb.append(c);
                    continue;
                }
                // Secuencia de escape: \n, \", á, ...
                if (fin()) {
                    throw new JsonException("Escape incompleto", pos);
                }
                char escape = texto.charAt(pos++);
                switch (escape) {
                    case '"' -> sb.append('"');
                    case '\\' -> sb.append('\\');
                    case '/' -> sb.append('/');
                    case 'n' -> sb.append('\n');
                    case 'r' -> sb.append('\r');
                    case 't' -> sb.append('\t');
                    case 'b' -> sb.append('\b');
                    case 'f' -> sb.append('\f');
                    case 'u' -> {
                        if (pos + 4 > texto.length()) {
                            throw new JsonException("Escape \\u incompleto", pos);
                        }
                        try {
                            sb.append((char) Integer.parseInt(texto.substring(pos, pos + 4), 16));
                        } catch (NumberFormatException e) {
                            throw new JsonException("Escape \\u no válido", pos);
                        }
                        pos += 4;
                    }
                    default -> throw new JsonException("Escape desconocido '\\" + escape + "'", pos - 1);
                }
            }
        }

        Number leerNumero() {
            int inicio = pos;
            boolean decimal = false;
            if (texto.charAt(pos) == '-') {
                pos++;
            }
            while (!fin()) {
                char c = texto.charAt(pos);
                if (Character.isDigit(c)) {
                    pos++;
                } else if (c == '.' || c == 'e' || c == 'E' || c == '+' || c == '-') {
                    decimal = true;
                    pos++;
                } else {
                    break;
                }
            }
            String numero = texto.substring(inicio, pos);
            try {
                if (decimal) {
                    return Double.parseDouble(numero);
                }
                return Long.parseLong(numero);
            } catch (NumberFormatException e) {
                throw new JsonException("Número no válido '" + numero + "'", inicio);
            }
        }

        void esperar(char esperado) {
            if (fin() || texto.charAt(pos) != esperado) {
                throw new JsonException("Se esperaba '" + esperado + "'", pos);
            }
            pos++;
        }
    }
}
