<?php
declare(strict_types=1);

namespace Kanban;

/**
 * Pinta plantillas PHP de la carpeta vistas/ dentro del layout común.
 */
final class Vista
{
    public function __construct(private string $carpeta)
    {
    }

    /** Renderiza una vista y la envuelve en layout.php. */
    public function render(string $nombre, array $datos = [], string $titulo = 'Kanban'): string
    {
        $contenido = $this->parcial($nombre, $datos);
        return $this->parcial('layout', ['contenido' => $contenido, 'titulo' => $titulo] + $datos);
    }

    /** Renderiza una plantilla suelta y devuelve el HTML como texto. */
    public function parcial(string $nombre, array $datos = []): string
    {
        $fichero = $this->carpeta . '/' . $nombre . '.php';
        if (!is_file($fichero)) {
            throw new \RuntimeException("No existe la vista $nombre");
        }
        extract($datos, EXTR_SKIP);
        ob_start();
        require $fichero;
        return (string) ob_get_clean();
    }
}

