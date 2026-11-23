<?php
declare(strict_types=1);

// Autoload sencillo (sin Composer): Kanban\Clase → src/Clase.php
spl_autoload_register(function (string $clase): void {
    $prefijo = 'Kanban\\';
    if (str_starts_with($clase, $prefijo)) {
        $fichero = __DIR__ . '/' . str_replace('\\', '/', substr($clase, strlen($prefijo))) . '.php';
        if (is_file($fichero)) {
            require $fichero;
        }
    }
});

// Funciones de ayuda globales para las plantillas (e(), ...)
require_once __DIR__ . '/funciones.php';
