<?php
declare(strict_types=1);

namespace Kanban;

use PDO;

/**
 * Conexión a SQLite con PDO y creación del esquema.
 * Se usa una única conexión por petición.
 */
final class BaseDatos
{
    /** Crea la conexión y, si hace falta, las tablas. ':memory:' sirve para los tests. */
    public static function conectar(string $ruta): PDO
    {
        if ($ruta !== ':memory:') {
            $dir = dirname($ruta);
            if (!is_dir($dir)) {
                mkdir($dir, 0775, true);
            }
        }
        $pdo = new PDO('sqlite:' . $ruta);
        // Errores como excepciones y filas como arrays asociativos
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
        // SQLite no activa las claves foráneas por defecto
        $pdo->exec('PRAGMA foreign_keys = ON');
        self::crearEsquema($pdo);
        return $pdo;
    }

    /** Tablas: tableros → columnas → tarjetas (borrado en cascada). */
    private static function crearEsquema(PDO $pdo): void
    {
        $pdo->exec(<<<SQL
            CREATE TABLE IF NOT EXISTS tableros (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre      TEXT    NOT NULL,
                descripcion TEXT    NOT NULL DEFAULT '',
                creado_en   TEXT    NOT NULL
            );
            CREATE TABLE IF NOT EXISTS columnas (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                tablero_id  INTEGER NOT NULL REFERENCES tableros(id) ON DELETE CASCADE,
                nombre      TEXT    NOT NULL,
                posicion    INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tarjetas (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                columna_id  INTEGER NOT NULL REFERENCES columnas(id) ON DELETE CASCADE,
                titulo      TEXT    NOT NULL,
                descripcion TEXT    NOT NULL DEFAULT '',
                posicion    INTEGER NOT NULL,
                creado_en   TEXT    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_columnas_tablero ON columnas(tablero_id);
            CREATE INDEX IF NOT EXISTS idx_tarjetas_columna ON tarjetas(columna_id);
        SQL);
    }
}
