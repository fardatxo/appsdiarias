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
    private Tarjetas $tarjetas;
    private Vista $vista;

    public function __construct(PDO $pdo, string $carpetaVistas)
    {
        $this->tableros = new Tableros($pdo);
        $this->tarjetas = new Tarjetas($pdo);
        $this->vista = new Vista($carpetaVistas);
        $this->router = new Router();
        $this->definirRutas();
    }

    /** Procesa una petición y devuelve [estado, cabeceras, cuerpo]. */
    public function manejar(string $metodo, string $uri, array $post = []): Respuesta
    {
        try {
            if ($metodo === 'POST') {
                Csrf::comprobar($post['_token'] ?? null);
            }
            $this->post = $post;
            $r = $this->router->despachar($metodo, $uri);
            return $r instanceof Respuesta ? $r : Respuesta::html((string) $r);
        } catch (ErrorHttp $e) {
            $html = $this->vista->render('error', ['estado' => $e->estado, 'mensaje' => $e->getMessage()], 'Error');
            return Respuesta::html($html, $e->estado);
        }
    }

    /** Datos del formulario de la petición actual */
    private array $post = [];

    private function definirRutas(): void
    {
        $r = $this->router;

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

        // Nueva tarjeta en una columna
        $r->post('/columnas/{id}/tarjetas', function (int $columnaId) {
            $columna = $this->tarjetas->columna($columnaId)
                ?? throw new ErrorHttp(404, 'Esa columna no existe');
            $tableroId = (int) $columna['tablero_id'];
            try {
                $this->tarjetas->crear($columnaId, $this->post['titulo'] ?? '', $this->post['descripcion'] ?? '');
                return Respuesta::redirigir("/tableros/$tableroId");
            } catch (ErrorValidacion $e) {
                return $this->pintarTablero($tableroId, [$columnaId => $e->errores], 422);
            }
        });
    }

    private function pintarTablero(int $id, array $erroresPorColumna = [], int $estado = 200): Respuesta
    {
        $tablero = $this->tableros->buscar($id) ?? throw new ErrorHttp(404, 'Ese tablero no existe');
        $html = $this->vista->render('tablero', [
            'tablero' => $tablero,
            'columnas' => $this->tableros->columnasConTarjetas($id),
            'erroresPorColumna' => $erroresPorColumna,
            'aviso' => $this->sacarAviso(),
        ], $tablero['nombre']);
        return Respuesta::html($html, $estado);
    }

    // Avisos "flash": se guardan en sesión y se muestran una sola vez
    private function ponerAviso(string $texto): void
    {
        $_SESSION['_aviso'] = $texto;
    }

    private function sacarAviso(): ?string
    {
        $texto = $_SESSION['_aviso'] ?? null;
        unset($_SESSION['_aviso']);
        return $texto;
    }
}
