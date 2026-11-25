<?php
declare(strict_types=1);

namespace Kanban;

/**
 * Convierte un tablero a JSON (estructura completa) o CSV (una fila por tarjeta).
 * Lo usan la API de solo lectura y los botones de exportar.
 */
final class Exportador
{
    public const CABECERA_CSV = ['columna', 'posicion', 'titulo', 'descripcion', 'etiqueta', 'fecha_limite', 'creado_en'];

    /** Estructura limpia para JSON: tipos correctos y sin campos internos. */
    public static function aArray(array $tablero, array $columnas): array
    {
        return [
            'id' => (int) $tablero['id'],
            'nombre' => $tablero['nombre'],
            'descripcion' => $tablero['descripcion'],
            'creado_en' => $tablero['creado_en'],
            'columnas' => array_map(fn (array $col) => [
                'id' => (int) $col['id'],
                'nombre' => $col['nombre'],
                'tarjetas' => array_map(fn (array $t) => [
                    'id' => (int) $t['id'],
                    'titulo' => $t['titulo'],
                    'descripcion' => $t['descripcion'],
                    'etiqueta' => $t['etiqueta'] !== '' ? $t['etiqueta'] : null,
                    'fecha_limite' => $t['fecha_limite'] !== '' ? $t['fecha_limite'] : null,
                    'creado_en' => $t['creado_en'],
                ], $col['tarjetas']),
            ], $columnas),
        ];
    }

    public static function json(array $tablero, array $columnas): string
    {
        return json_encode(
            self::aArray($tablero, $columnas),
            JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR,
        );
    }

    /** CSV con BOM UTF-8 (para que Excel muestre bien las tildes) y separador coma. */
    public static function csv(array $columnas): string
    {
        $f = fopen('php://temp', 'r+');
        fwrite($f, "\xEF\xBB\xBF");
        fputcsv($f, self::CABECERA_CSV, ',', '"', '');
        foreach ($columnas as $col) {
            foreach ($col['tarjetas'] as $pos => $t) {
                $fila = [$col['nombre'], $pos + 1, $t['titulo'], $t['descripcion'], $t['etiqueta'], $t['fecha_limite'], $t['creado_en']];
                fputcsv($f, array_map([self::class, 'celdaSegura'], $fila), ',', '"', '');
            }
        }
        rewind($f);
        $csv = stream_get_contents($f);
        fclose($f);
        return $csv;
    }

    /**
     * Evita la "inyección de fórmulas": una hoja de cálculo ejecutaría
     * "=HYPERLINK(...)" como fórmula. Se antepone una comilla simple.
     */
    public static function celdaSegura(mixed $valor): string
    {
        $valor = (string) $valor;
        return $valor !== '' && in_array($valor[0], ['=', '+', '-', '@', "\t", "\r"], true) ? "'" . $valor : $valor;
    }

    /** Nombre de fichero seguro: "Mi tablero!" → "mi-tablero" */
    public static function nombreFichero(string $nombre, string $extension): string
    {
        $base = trim(preg_replace('/[^a-z0-9]+/', '-', normalizar($nombre)), '-');
        return ($base !== '' ? $base : 'tablero') . '.' . $extension;
    }
}
