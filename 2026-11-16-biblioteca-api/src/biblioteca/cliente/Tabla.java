package biblioteca.cliente;

import java.io.PrintStream;
import java.util.ArrayList;
import java.util.List;

/** Tabla de texto con columnas alineadas; recorta los textos muy largos con "…". */
final class Tabla {

    static final int ANCHO_MAXIMO_COLUMNA = 32;

    private final String[] cabecera;
    private final List<String[]> filas = new ArrayList<>();

    Tabla(String... cabecera) {
        this.cabecera = cabecera;
    }

    void fila(Object... celdas) {
        if (celdas.length != cabecera.length) {
            throw new IllegalArgumentException("La fila tiene " + celdas.length + " celdas y la cabecera "
                    + cabecera.length);
        }
        String[] textos = new String[celdas.length];
        for (int i = 0; i < celdas.length; i++) {
            textos[i] = recortar(celdas[i] == null ? "" : String.valueOf(celdas[i]), ANCHO_MAXIMO_COLUMNA);
        }
        filas.add(textos);
    }

    void imprimir(PrintStream out) {
        // Ancho de cada columna = el texto más largo de esa columna
        int[] anchos = new int[cabecera.length];
        for (int i = 0; i < cabecera.length; i++) {
            anchos[i] = cabecera[i].length();
            for (String[] fila : filas) {
                anchos[i] = Math.max(anchos[i], fila[i].length());
            }
        }
        out.println(linea(cabecera, anchos));
        StringBuilder separador = new StringBuilder();
        for (int i = 0; i < anchos.length; i++) {
            separador.append(i == 0 ? "" : "  ").append("-".repeat(anchos[i]));
        }
        out.println(separador.toString().stripTrailing());
        for (String[] fila : filas) {
            out.println(linea(fila, anchos));
        }
    }

    private static String linea(String[] celdas, int[] anchos) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < celdas.length; i++) {
            if (i > 0) {
                sb.append("  ");
            }
            sb.append(celdas[i]).append(" ".repeat(anchos[i] - celdas[i].length()));
        }
        return sb.toString().stripTrailing();
    }

    /** "Un título larguísimo" -> "Un título lar…" si no cabe en el ancho. */
    static String recortar(String texto, int ancho) {
        return texto.length() <= ancho ? texto : texto.substring(0, ancho - 1) + "…";
    }
}
