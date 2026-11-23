<?php
declare(strict_types=1);

namespace Kanban;

/**
 * Router mínimo: asocia "MÉTODO /ruta/{id}" a una función.
 * Los {parametros} se convierten en argumentos enteros.
 */
final class Router
{
    /** @var array<int,array{0:string,1:string,2:callable}> */
    private array $rutas = [];

    public function get(string $patron, callable $accion): void
    {
        $this->rutas[] = ['GET', $patron, $accion];
    }

    public function post(string $patron, callable $accion): void
    {
        $this->rutas[] = ['POST', $patron, $accion];
    }

    /**
     * Busca la ruta y la ejecuta. Devuelve lo que devuelva la acción.
     * Lanza NoEncontrado (404) o MetodoNoPermitido (405).
     */
    public function despachar(string $metodo, string $uri): mixed
    {
        $ruta = rtrim(parse_url($uri, PHP_URL_PATH) ?: '/', '/') ?: '/';
        $metodosValidos = [];

        foreach ($this->rutas as [$m, $patron, $accion]) {
            // "/tableros/{id}" → "#^/tableros/(\d+)$#"
            $regex = '#^' . preg_replace('#\{\w+\}#', '(\d+)', $patron) . '$#';
            if (preg_match($regex, $ruta, $coincidencias)) {
                if ($m !== $metodo) {
                    $metodosValidos[] = $m;
                    continue;
                }
                $args = array_map('intval', array_slice($coincidencias, 1));
                return $accion(...$args);
            }
        }
        if ($metodosValidos) {
            throw new ErrorHttp(405, 'Método no permitido');
        }
        throw new ErrorHttp(404, 'Página no encontrada');
    }
}
