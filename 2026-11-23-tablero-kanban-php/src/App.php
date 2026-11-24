<?php
declare(strict_types=1);

namespace Kanban;

use PDO;

/**
 * Une todo: define las rutas, llama a los repositorios y devuelve
 * una Respuesta. No toca superglobales salvo $_SESSION (CSRF y avisos),
 * así se puede probar desde los tests.
 */
final class App
{
    private Router $router;
    private Tableros $tableros;
    private Columnas $columnas;
    private Tarjetas $tarjetas;
    private Vista $vista;

    /** Datos del formulario de la petición actual */
    private array $post = [];

    public function __construct(PDO $pdo, string $carpetaVistas)
    {
        $this->tableros = new Tableros($pdo);
        $this->columnas = new Columnas($pdo);
        $this->tarjetas = new Tarjetas($pdo);
        $this->vista = new Vista($carpetaVistas);
        $this->router = new Router();
        $this->definirRutas();
    }

    /** Procesa una petición y devuelve una Respuesta. */
    public function manejar(string $metodo, string $uri, array $post = []): Respuesta
    {
        $this->post = $post;
        try {
            if ($metodo === 'POST') {
                Csrf::comprobar($post['_token'] ?? null);
            }
            $r = $this->router->despachar($metodo, $uri);
            return $r instanceof Respuesta ? $r : Respuesta::html((string) $r);
        } catch (ErrorHttp $e) {
            if ($this->esAjax()) {
                return Respuesta::json(['ok' => false, 'error' => $e->getMessage()], $e->estado);
            }
            $html = $this->vista->render('error', ['estado' => $e->estado, 'mensaje' => $e->getMessage()], 'Error');
            return Respuesta::html($html, $e->estado);
        }
    }

    private function definirRutas(): void
    {
        $r = $this->router;

        // ---------- Tableros ----------

        // Portada: lista de tableros + formulario para crear uno
        $r->get('/', fn () => $this->vista->render('tableros', [
            'tableros' => $this->tableros->listar(),
            'aviso' => $this->sacarAviso(),
        ], 'Mis tableros'));

        $r->post('/tableros', function () {
            try {
                $id = $this->tableros->crear($this->post['nombre'] ?? '', $this->post['descripcion'] ?? '');
                $this->ponerAviso('Tablero creado.');
                return Respuesta::redirigir("/tableros/$id");
            } catch (ErrorValidacion $e) {
                // Volvemos a pintar la portada con los errores y lo que escribió el usuario
                return Respuesta::html($this->vista->render('tableros', [
                    'tableros' => $this->tableros->listar(),
                    'errores' => $e->errores,
                    'viejo' => $this->post,
                ], 'Mis tableros'), 422);
            }
        });

        // Vista de un tablero con sus columnas y tarjetas
        $r->get('/tableros/{id}', fn (int $id) => $this->pintarTablero($id));

        $r->post('/tableros/{id}/borrar', function (int $id) {
            if (!$this->tableros->borrar($id)) {
                throw new ErrorHttp(404, 'Ese tablero no existe');
            }
            $this->ponerAviso('Tablero borrado.');
            return Respuesta::redirigir('/');
        });

        // ---------- Columnas ----------

        $r->post('/tableros/{id}/columnas', function (int $tableroId) {
            $this->tableros->buscar($tableroId) ?? throw new ErrorHttp(404, 'Ese tablero no existe');
            return $this->accionConAviso($tableroId, function () use ($tableroId) {
                $this->columnas->crear($tableroId, $this->post['nombre'] ?? '');
                return 'Columna añadida.';
            });
        });

        $r->post('/columnas/{id}', function (int $id) {
            $col = $this->columnaOError($id);
            return $this->accionConAviso((int) $col['tablero_id'], function () use ($id) {
                $this->columnas->renombrar($id, $this->post['nombre'] ?? '');
                return 'Columna renombrada.';
            });
        });

        $r->post('/columnas/{id}/borrar', function (int $id) {
            $col = $this->columnaOError($id);
            return $this->accionConAviso((int) $col['tablero_id'], function () use ($id) {
                $this->columnas->borrar($id);
                return 'Columna borrada.';
            });
        });

        $r->post('/columnas/{id}/mover', function (int $id) {
            $col = $this->columnaOError($id);
            $sentido = ($this->post['direccion'] ?? '') === 'izquierda' ? -1 : 1;
            $this->columnas->desplazar($id, $sentido);
            return Respuesta::redirigir('/tableros/' . $col['tablero_id']);
        });

        // ---------- Tarjetas ----------

        // Nueva tarjeta en una columna
        $r->post('/columnas/{id}/tarjetas', function (int $columnaId) {
            $tableroId = (int) $this->columnaOError($columnaId)['tablero_id'];
            try {
                $this->tarjetas->crear(
                    $columnaId,
                    $this->post['titulo'] ?? '',
                    $this->post['descripcion'] ?? '',
                    $this->post['etiqueta'] ?? '',
                    $this->post['fecha_limite'] ?? '',
                );
                return Respuesta::redirigir("/tableros/$tableroId#col-$columnaId");
            } catch (ErrorValidacion $e) {
                return $this->pintarTablero($tableroId, [$columnaId => $e->errores], 422, [$columnaId => $this->post]);
            }
        });

        // Formulario de edición
        $r->get('/tarjetas/{id}/editar', function (int $id) {
            return $this->pintarEdicion($this->tarjetaOError($id));
        });

        $r->post('/tarjetas/{id}', function (int $id) {
            $tarjeta = $this->tarjetaOError($id);
            try {
                $this->tarjetas->actualizar(
                    $id,
                    $this->post['titulo'] ?? '',
                    $this->post['descripcion'] ?? '',
                    $this->post['etiqueta'] ?? '',
                    $this->post['fecha_limite'] ?? '',
                );
                $this->ponerAviso('Tarjeta guardada.');
                return Respuesta::redirigir('/tableros/' . $tarjeta['tablero_id']);
            } catch (ErrorValidacion $e) {
                return $this->pintarEdicion(array_merge($tarjeta, $this->post), $e->errores, 422);
            }
        });

        $r->post('/tarjetas/{id}/borrar', function (int $id) {
            $tarjeta = $this->tarjetaOError($id);
            $this->tarjetas->borrar($id);
            $this->ponerAviso('Tarjeta borrada.');
            return Respuesta::redirigir('/tableros/' . $tarjeta['tablero_id']);
        });

        /*
         * Mover una tarjeta. Dos formas:
         *  - direccion=arriba|abajo|izquierda|derecha  (botones, sin JS)
         *  - columna_id + posicion                     (arrastrar y soltar con JS, ajax=1)
         */
        $r->post('/tarjetas/{id}/mover', function (int $id) {
            $tarjeta = $this->tarjetaOError($id);
            try {
                if (isset($this->post['direccion'])) {
                    $this->tarjetas->moverRelativo($id, (string) $this->post['direccion']);
                } else {
                    $this->tarjetas->mover($id, (int) ($this->post['columna_id'] ?? 0), (int) ($this->post['posicion'] ?? 0));
                }
            } catch (ErrorValidacion $e) {
                if ($this->esAjax()) {
                    return Respuesta::json(['ok' => false, 'error' => $e->getMessage()], 422);
                }
                $this->ponerAviso($e->getMessage(), 'error');
            }
            if ($this->esAjax()) {
                return Respuesta::json(['ok' => true]);
            }
            return Respuesta::redirigir('/tableros/' . $tarjeta['tablero_id'] . '#tarjeta-' . $id);
        });
    }

    /** Ejecuta una acción que devuelve un aviso; si falla la validación, avisa del error. */
    private function accionConAviso(int $tableroId, callable $accion): Respuesta
    {
        try {
            $this->ponerAviso($accion());
        } catch (ErrorValidacion $e) {
            $this->ponerAviso($e->getMessage(), 'error');
        }
        return Respuesta::redirigir("/tableros/$tableroId");
    }

    private function columnaOError(int $id): array
    {
        return $this->columnas->buscar($id) ?? throw new ErrorHttp(404, 'Esa columna no existe');
    }

    private function tarjetaOError(int $id): array
    {
        return $this->tarjetas->buscar($id) ?? throw new ErrorHttp(404, 'Esa tarjeta no existe');
    }

    private function esAjax(): bool
    {
        return ($this->post['ajax'] ?? '') === '1';
    }

    private function pintarTablero(int $id, array $erroresPorColumna = [], int $estado = 200, array $viejoPorColumna = []): Respuesta
    {
        $tablero = $this->tableros->buscar($id) ?? throw new ErrorHttp(404, 'Ese tablero no existe');
        $html = $this->vista->render('tablero', [
            'tablero' => $tablero,
            'columnas' => $this->tableros->columnasConTarjetas($id),
            'erroresPorColumna' => $erroresPorColumna,
            'viejoPorColumna' => $viejoPorColumna,
            'aviso' => $this->sacarAviso(),
        ], $tablero['nombre']);
        return Respuesta::html($html, $estado);
    }

    private function pintarEdicion(array $tarjeta, array $errores = [], int $estado = 200): Respuesta
    {
        $tablero = $this->tableros->buscar((int) $tarjeta['tablero_id']);
        $html = $this->vista->render('editar-tarjeta', [
            'tarjeta' => $tarjeta,
            'tablero' => $tablero,
            'errores' => $errores,
        ], 'Editar tarjeta');
        return Respuesta::html($html, $estado);
    }

    // Avisos "flash": se guardan en sesión y se muestran una sola vez
    private function ponerAviso(string $texto, string $tipo = 'ok'): void
    {
        $_SESSION['_aviso'] = ['texto' => $texto, 'tipo' => $tipo];
    }

    private function sacarAviso(): ?array
    {
        $aviso = $_SESSION['_aviso'] ?? null;
        unset($_SESSION['_aviso']);
        return $aviso;
    }
}
