<?php
declare(strict_types=1);

namespace Kanban;

use PDO;

/**
 * Repositorio de tableros y sus columnas.
 * Toda la SQL de tableros vive aquí; las vistas solo reciben arrays.
 */
final class Tableros
{
    /** Columnas que se crean con cada tablero nuevo */
    public const COLUMNAS_INICIALES = ['Por hacer', 'En curso', 'Hecho'];

    public const MAX_NOMBRE = 80;
    public const MAX_DESCRIPCION = 500;

    public function __construct(private PDO $pdo)
    {
    }

    /** Lista todos los tableros con el número de tarjetas de cada uno. */
    public function listar(): array
    {
        $sql = 'SELECT t.*, COUNT(ta.id) AS num_tarjetas
                FROM tableros t
                LEFT JOIN columnas c  ON c.tablero_id = t.id
                LEFT JOIN tarjetas ta ON ta.columna_id = c.id
                GROUP BY t.id
                ORDER BY t.id DESC';
        return $this->pdo->query($sql)->fetchAll();
    }

    public function buscar(int $id): ?array
    {
        $st = $this->pdo->prepare('SELECT * FROM tableros WHERE id = ?');
        $st->execute([$id]);
        return $st->fetch() ?: null;
    }

    /**
     * Crea un tablero con las columnas iniciales dentro de una transacción.
     * Devuelve el id nuevo o lanza ErrorValidacion.
     */
    public function crear(string $nombre, string $descripcion = ''): int
    {
        [$nombre, $descripcion] = $this->validar($nombre, $descripcion);

        $this->pdo->beginTransaction();
        try {
            $st = $this->pdo->prepare(
                'INSERT INTO tableros (nombre, descripcion, creado_en) VALUES (?, ?, ?)'
            );
            $st->execute([$nombre, $descripcion, date('c')]);
            $id = (int) $this->pdo->lastInsertId();

            $stCol = $this->pdo->prepare(
                'INSERT INTO columnas (tablero_id, nombre, posicion) VALUES (?, ?, ?)'
            );
            foreach (self::COLUMNAS_INICIALES as $pos => $col) {
                $stCol->execute([$id, $col, $pos]);
            }
            $this->pdo->commit();
            return $id;
        } catch (\Throwable $e) {
            $this->pdo->rollBack();
            throw $e;
        }
    }

    /** Borra el tablero; columnas y tarjetas caen en cascada. */
    public function borrar(int $id): bool
    {
        $st = $this->pdo->prepare('DELETE FROM tableros WHERE id = ?');
        $st->execute([$id]);
        return $st->rowCount() > 0;
    }

    /**
     * Devuelve las columnas del tablero, cada una con su lista de tarjetas
     * ya ordenada. Así la vista pinta el tablero con un solo array.
     */
    public function columnasConTarjetas(int $tableroId): array
    {
        $st = $this->pdo->prepare(
            'SELECT * FROM columnas WHERE tablero_id = ? ORDER BY posicion, id'
        );
        $st->execute([$tableroId]);
        $columnas = [];
        foreach ($st->fetchAll() as $col) {
            $col['tarjetas'] = [];
            $columnas[(int) $col['id']] = $col;
        }
        if (!$columnas) {
            return [];
        }

        // Una sola consulta para todas las tarjetas del tablero
        $st = $this->pdo->prepare(
            'SELECT ta.* FROM tarjetas ta
             JOIN columnas c ON c.id = ta.columna_id
             WHERE c.tablero_id = ?
             ORDER BY ta.posicion, ta.id'
        );
        $st->execute([$tableroId]);
        foreach ($st->fetchAll() as $tarjeta) {
            $columnas[(int) $tarjeta['columna_id']]['tarjetas'][] = $tarjeta;
        }
        return array_values($columnas);
    }

    /** Limpia espacios y comprueba longitudes. */
    private function validar(string $nombre, string $descripcion): array
    {
        $nombre = trim($nombre);
        $descripcion = trim($descripcion);
        $errores = [];
        if ($nombre === '') {
            $errores['nombre'] = 'El nombre es obligatorio.';
        } elseif (mb_strlen($nombre) > self::MAX_NOMBRE) {
            $errores['nombre'] = 'El nombre no puede pasar de ' . self::MAX_NOMBRE . ' caracteres.';
        }
        if (mb_strlen($descripcion) > self::MAX_DESCRIPCION) {
            $errores['descripcion'] = 'La descripción es demasiado larga.';
        }
        if ($errores) {
            throw new ErrorValidacion($errores);
        }
        return [$nombre, $descripcion];
    }
}
