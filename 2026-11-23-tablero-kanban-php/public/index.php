<?php
declare(strict_types=1);

// Controlador frontal: todas las peticiones pasan por aquí.
// Arranque:  php -S localhost:8000 -t public public/index.php

// Con el servidor integrado, los ficheros estáticos (CSS) se sirven tal cual
if (PHP_SAPI === 'cli-server') {
    $fichero = __DIR__ . parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
    if (is_file($fichero) && $fichero !== __FILE__) {
        return false;
    }
}

require __DIR__ . '/../src/autoload.php';

use Kanban\App;
use Kanban\BaseDatos;

session_start();

// La ruta de la base de datos se puede cambiar con la variable KANBAN_DB
$rutaDb = getenv('KANBAN_DB') ?: __DIR__ . '/../datos/kanban.sqlite';
$pdo = BaseDatos::conectar($rutaDb);

$app = new App($pdo, __DIR__ . '/../vistas');
$app->manejar($_SERVER['REQUEST_METHOD'] ?? 'GET', $_SERVER['REQUEST_URI'] ?? '/', $_POST)->enviar();
