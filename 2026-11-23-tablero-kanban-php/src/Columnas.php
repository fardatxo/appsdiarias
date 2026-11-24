<?php
declare(strict_types=1);

namespace Kanban;

use PDO;

/**
 * Repositorio de columnas: añadir, renombrar, borrar y reordenar.
 * Igual que con las tarjetas, las posiciones se mantienen en 0..n-1.
 */
final class Columnas
{
    public const MAX_NOMBRE = 40;
    public const MAX_POR_TABLERO = 10;

    public function __construct(private PDO $pdo)
    {
    }

    public function buscar(int $id): ?array
    {
        $st = $this->pdo->prepare('SELECT * FROM columnas WHERE id = ?');
        $st->execute([$id]);
        return $st->fetch() ?: null;
    }

    /** Añade una columna al final del tablero. */
    public function crear(int $tableroId, string $nombre): int
    {
        $nombre = $this->validar($nombre);
        $total = $this->contar($tableroId);
        if ($total >= self::MAX_POR_TABLERO) {
            throw new ErrorValidacion(['nombre' => 'Un tablero admite como mucho ' . self::MAX_POR_TABLERO . ' columnas.']);
        }
        $st = $this->pdo->prepare('INSERT INTO columnas (tablero_id, nombre, posicion) VALUES (?, ?, ?)');
        $st->execute([$tableroId, $nombre, $total]);
        return (int) $this->pdo->lastInsertId();
    }

    public function renombrar(int $id, string $nombre): void
    {
        $nombre = $this->validar($nombre);
        $this->pdo->prepare('UPDATE columnas SET nombre = ? WHERE id = ?')->execute([$nombre, $id]);
    }

    /** Borra la columna (sus tarjetas caen en cascada). No deja borrar la última. */
    public function borrar(int $id): void
    {
        $col = $this->buscar($id) ?? throw new ErrorHttp(404, 'Esa columna no existe');
        if ($this->contar((int) $col['tablero_id']) <= 1) {
            throw new ErrorValidacion(['columna' => 'Un tablero necesita al menos una columna.']);
        }
        $this->pdo->beginTransaction();
        try {
            $this->pdo->prepare('DELETE FROM columnas WHERE id = ?')->execute([$id]);
            $this->pdo->prepare(
                'UPDATE columnas SET posicion = posicion - 1 WHERE tablero_id = ? AND posicion > ?'
            )->execute([$col['tablero_id'], $col['posicion']]);
            $this->pdo->commit();
        } catch (\Throwable $e) {
            $this->pdo->rollBack();
            throw $e;
        }
    }

    /** Intercambia la columna con su vecina (-1 izquierda, +1 derecha). */
    public function desplazar(int $id, int $sentido): bool
    {
        $col = $this->buscar($id) ?? throw new ErrorHttp(404, 'Esa columna no existe');
        $st = $this->pdo->prepare('SELECT * FROM columnas WHERE tablero_id = ? AND posicion = ?');
        $st->execute([$col['tablero_id'], (int) $col['posicion'] + $sentido]);
        $vecina = $st->fetch();
        if (!$vecina) {
            return false;
        }
        $upd = $this->pdo->prepare('UPDATE columnas SET posicion = ? WHERE id = ?');
        $this->pdo->beginTransaction();
        $upd->execute([$vecina['posicion'], $col['id']]);
        $upd->execute([$col['posicion'], $vecina['id']]);
        $this->pdo->commit();
        return true;
    }

    public function contar(int $tableroId): int
    {
        $st = $this->pdo->prepare('SELECT COUNT(*) FROM columnas WHERE tablero_id = ?');
        $st->execute([$tableroId]);
        return (int) $st->fetchColumn();
    }

    private function validar(string $nombre): string
    {
        $nombre = trim($nombre);
        if ($nombre === '') {
            throw new ErrorValidacion(['nombre' => 'El nombre de la columna es obligatorio.']);
        }
        if (mb_strlen($nombre) > self::MAX_NOMBRE) {
            throw new ErrorValidacion(['nombre' => 'El nombre no puede pasar de ' . self::MAX_NOMBRE . ' caracteres.']);
        }
        return $nombre;
    }
}
