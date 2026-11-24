<?php
declare(strict_types=1);

namespace Kanban;

use PDO;

/**
 * Repositorio de tarjetas. Cada tarjeta pertenece a una columna y
 * tiene una posición (0, 1, 2...) dentro de ella. Las operaciones que
 * cambian posiciones mantienen siempre la secuencia 0..n-1 sin huecos.
 */
final class Tarjetas
{
    public const MAX_TITULO = 120;
    public const MAX_DESCRIPCION = 2000;

    /** Etiquetas de color disponibles: clave guardada en BD => nombre visible */
    public const ETIQUETAS = [
        'rojo' => 'Urgente',
        'naranja' => 'Importante',
        'amarillo' => 'En espera',
        'verde' => 'Fácil',
        'azul' => 'Idea',
        'morado' => 'Bug',
    ];

    /** Direcciones aceptadas por moverRelativo() */
    public const DIRECCIONES = ['arriba', 'abajo', 'izquierda', 'derecha'];

    public function __construct(private PDO $pdo)
    {
    }

    public function buscar(int $id): ?array
    {
        $st = $this->pdo->prepare(
            'SELECT ta.*, c.tablero_id FROM tarjetas ta JOIN columnas c ON c.id = ta.columna_id WHERE ta.id = ?'
        );
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
    public function crear(int $columnaId, string $titulo, string $descripcion = '', string $etiqueta = '', string $fechaLimite = ''): int
    {
        $errores = [];
        if ($this->columna($columnaId) === null) {
            $errores['columna'] = 'La columna no existe.';
        }
        $datos = $this->validar($titulo, $descripcion, $etiqueta, $fechaLimite, $errores);

        $st = $this->pdo->prepare(
            'INSERT INTO tarjetas (columna_id, titulo, descripcion, etiqueta, fecha_limite, posicion, creado_en)
             VALUES (?, ?, ?, ?, ?, ?, ?)'
        );
        $st->execute([$columnaId, ...$datos, $this->contar($columnaId), date('c')]);
        return (int) $this->pdo->lastInsertId();
    }

    /** Cambia los datos de una tarjeta (no su columna ni su posición). */
    public function actualizar(int $id, string $titulo, string $descripcion = '', string $etiqueta = '', string $fechaLimite = ''): bool
    {
        $datos = $this->validar($titulo, $descripcion, $etiqueta, $fechaLimite);
        $st = $this->pdo->prepare(
            'UPDATE tarjetas SET titulo = ?, descripcion = ?, etiqueta = ?, fecha_limite = ? WHERE id = ?'
        );
        $st->execute([...$datos, $id]);
        return $st->rowCount() > 0 || $this->buscar($id) !== null;
    }

    /** Borra la tarjeta y cierra el hueco que deja en su columna. */
    public function borrar(int $id): bool
    {
        $tarjeta = $this->buscar($id);
        if ($tarjeta === null) {
            return false;
        }
        $this->enTransaccion(function () use ($tarjeta) {
            $this->pdo->prepare('DELETE FROM tarjetas WHERE id = ?')->execute([$tarjeta['id']]);
            $this->cerrarHueco((int) $tarjeta['columna_id'], (int) $tarjeta['posicion']);
        });
        return true;
    }

    /**
     * Mueve la tarjeta a la columna indicada (del mismo tablero) y la deja
     * en la posición pedida (se ajusta a los límites). Lo usa el arrastrar y soltar.
     */
    public function mover(int $id, int $columnaDestino, int $posicion): void
    {
        $tarjeta = $this->buscar($id) ?? throw new ErrorHttp(404, 'Esa tarjeta no existe');
        $destino = $this->columna($columnaDestino);
        if ($destino === null || (int) $destino['tablero_id'] !== (int) $tarjeta['tablero_id']) {
            throw new ErrorValidacion(['columna' => 'La columna de destino no es válida.']);
        }
        $origen = (int) $tarjeta['columna_id'];

        $this->enTransaccion(function () use ($tarjeta, $origen, $columnaDestino, $posicion) {
            // 1) Sacamos la tarjeta de su columna (posición -1 = "en el aire")
            $this->pdo->prepare('UPDATE tarjetas SET posicion = -1 WHERE id = ?')->execute([$tarjeta['id']]);
            $this->cerrarHueco($origen, (int) $tarjeta['posicion']);

            // 2) Abrimos hueco en el destino y la colocamos
            $total = $this->contar($columnaDestino) - ($origen === $columnaDestino ? 1 : 0);
            $posicion = max(0, min($posicion, $total));
            $this->pdo->prepare(
                'UPDATE tarjetas SET posicion = posicion + 1 WHERE columna_id = ? AND posicion >= ?'
            )->execute([$columnaDestino, $posicion]);
            $this->pdo->prepare('UPDATE tarjetas SET columna_id = ?, posicion = ? WHERE id = ?')
                ->execute([$columnaDestino, $posicion, $tarjeta['id']]);
        });
    }

    /**
     * Movimiento con los botones ← → ↑ ↓ (funciona sin JavaScript).
     * Izquierda/derecha la lleva al final de la columna vecina.
     * Devuelve false si no se puede mover más en esa dirección.
     */
    public function moverRelativo(int $id, string $direccion): bool
    {
        $tarjeta = $this->buscar($id) ?? throw new ErrorHttp(404, 'Esa tarjeta no existe');
        $pos = (int) $tarjeta['posicion'];
        $columnaId = (int) $tarjeta['columna_id'];

        switch ($direccion) {
            case 'arriba':
                if ($pos === 0) {
                    return false;
                }
                $this->mover($id, $columnaId, $pos - 1);
                return true;
            case 'abajo':
                if ($pos >= $this->contar($columnaId) - 1) {
                    return false;
                }
                $this->mover($id, $columnaId, $pos + 1);
                return true;
            case 'izquierda':
            case 'derecha':
                $vecina = $this->columnaVecina($columnaId, $direccion === 'izquierda' ? -1 : 1);
                if ($vecina === null) {
                    return false;
                }
                $this->mover($id, $vecina, PHP_INT_MAX);
                return true;
            default:
                throw new ErrorValidacion(['direccion' => 'Dirección no válida.']);
        }
    }

    /** Número de tarjetas de una columna. */
    public function contar(int $columnaId): int
    {
        $st = $this->pdo->prepare('SELECT COUNT(*) FROM tarjetas WHERE columna_id = ?');
        $st->execute([$columnaId]);
        return (int) $st->fetchColumn();
    }

    /** Id de la columna de al lado (-1 izquierda, +1 derecha) o null si no hay. */
    private function columnaVecina(int $columnaId, int $sentido): ?int
    {
        $col = $this->columna($columnaId);
        $st = $this->pdo->prepare('SELECT id FROM columnas WHERE tablero_id = ? ORDER BY posicion, id');
        $st->execute([$col['tablero_id']]);
        $ids = array_map('intval', $st->fetchAll(PDO::FETCH_COLUMN));
        $i = array_search($columnaId, $ids, true);
        return $ids[$i + $sentido] ?? null;
    }

    /** Baja una posición todas las tarjetas que estaban por debajo del hueco. */
    private function cerrarHueco(int $columnaId, int $posicion): void
    {
        $this->pdo->prepare(
            'UPDATE tarjetas SET posicion = posicion - 1 WHERE columna_id = ? AND posicion > ?'
        )->execute([$columnaId, $posicion]);
    }

    private function enTransaccion(callable $fn): void
    {
        $this->pdo->beginTransaction();
        try {
            $fn();
            $this->pdo->commit();
        } catch (\Throwable $e) {
            $this->pdo->rollBack();
            throw $e;
        }
    }

    /**
     * Limpia y valida los campos. Devuelve [titulo, descripcion, etiqueta, fecha]
     * o lanza ErrorValidacion con todos los errores juntos.
     */
    private function validar(string $titulo, string $descripcion, string $etiqueta, string $fecha, array $errores = []): array
    {
        $titulo = trim($titulo);
        $descripcion = trim($descripcion);
        $etiqueta = trim($etiqueta);
        $fecha = trim($fecha);

        if ($titulo === '') {
            $errores['titulo'] = 'El título es obligatorio.';
        } elseif (mb_strlen($titulo) > self::MAX_TITULO) {
            $errores['titulo'] = 'El título no puede pasar de ' . self::MAX_TITULO . ' caracteres.';
        }
        if (mb_strlen($descripcion) > self::MAX_DESCRIPCION) {
            $errores['descripcion'] = 'La descripción es demasiado larga.';
        }
        if ($etiqueta !== '' && !isset(self::ETIQUETAS[$etiqueta])) {
            $errores['etiqueta'] = 'Etiqueta no válida.';
        }
        if ($fecha !== '' && !fecha_valida($fecha)) {
            $errores['fecha_limite'] = 'La fecha debe tener el formato AAAA-MM-DD.';
        }
        if ($errores) {
            throw new ErrorValidacion($errores);
        }
        return [$titulo, $descripcion, $etiqueta, $fecha];
    }
}
