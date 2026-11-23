<?php
declare(strict_types=1);

namespace Kanban;

use PDO;

/**
 * Repositorio de tarjetas. Cada tarjeta pertenece a una columna y
 * tiene una posición (0, 1, 2...) dentro de ella.
 */
final class Tarjetas
{
    public const MAX_TITULO = 120;
    public const MAX_DESCRIPCION = 2000;

    public function __construct(private PDO $pdo)
    {
    }

    public function buscar(int $id): ?array
    {
        $st = $this->pdo->prepare('SELECT * FROM tarjetas WHERE id = ?');
        $st->execute([$id]);
        return $st->fetch() ?: null;
    }

    /** Devuelve la columna si existe (para validar y saber a qué tablero volver). */
    public function columna(int $columnaId): ?array
    {
        $st = $this->pdo->prepare('SELECT * FROM columnas WHERE id = ?');
        $st->execute([$columnaId]);
        return $st->fetch() ?: null;
    }

    /** Crea una tarjeta al final de la columna y devuelve su id. */
    public function crear(int $columnaId, string $titulo, string $descripcion = ''): int
    {
        $titulo = trim($titulo);
        $descripcion = trim($descripcion);
        $errores = [];
        if ($this->columna($columnaId) === null) {
            $errores['columna'] = 'La columna no existe.';
        }
        if ($titulo === '') {
            $errores['titulo'] = 'El título es obligatorio.';
        } elseif (mb_strlen($titulo) > self::MAX_TITULO) {
            $errores['titulo'] = 'El título no puede pasar de ' . self::MAX_TITULO . ' caracteres.';
        }
        if (mb_strlen($descripcion) > self::MAX_DESCRIPCION) {
            $errores['descripcion'] = 'La descripción es demasiado larga.';
        }
        if ($errores) {
            throw new ErrorValidacion($errores);
        }

        $st = $this->pdo->prepare(
            'INSERT INTO tarjetas (columna_id, titulo, descripcion, posicion, creado_en)
             VALUES (?, ?, ?, ?, ?)'
        );
        $st->execute([$columnaId, $titulo, $descripcion, $this->siguientePosicion($columnaId), date('c')]);
        return (int) $this->pdo->lastInsertId();
    }

    /** Siguiente hueco libre al final de la columna. */
    private function siguientePosicion(int $columnaId): int
    {
        $st = $this->pdo->prepare('SELECT COALESCE(MAX(posicion) + 1, 0) FROM tarjetas WHERE columna_id = ?');
        $st->execute([$columnaId]);
        return (int) $st->fetchColumn();
    }
}
