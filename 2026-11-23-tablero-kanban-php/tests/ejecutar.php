<?php
declare(strict_types=1);

// Mini runner de tests sin PHPUnit: php tests/ejecutar.php
// Cada función test_* se ejecuta con una base de datos SQLite en memoria nueva.

require __DIR__ . '/../src/autoload.php';

use Kanban\App;
use Kanban\BaseDatos;
use Kanban\ErrorHttp;
use Kanban\ErrorValidacion;
use Kanban\Router;
use Kanban\Tableros;
use Kanban\Tarjetas;

$_SESSION = [];

function comprobar(bool $condicion, string $mensaje = 'la condición es falsa'): void
{
    if (!$condicion) {
        throw new AssertionError($mensaje);
    }
}

function igual(mixed $esperado, mixed $real, string $que = ''): void
{
    if ($esperado !== $real) {
        throw new AssertionError(sprintf('%s esperado %s, obtenido %s', $que, var_export($esperado, true), var_export($real, true)));
    }
}

/** Comprueba que $fn lanza una excepción de la clase indicada y la devuelve. */
function lanza(string $clase, callable $fn): Throwable
{
    try {
        $fn();
    } catch (Throwable $e) {
        comprobar($e instanceof $clase, "se esperaba $clase y llegó " . $e::class);
        return $e;
    }
    throw new AssertionError("se esperaba la excepción $clase");
}

function bd(): PDO
{
    return BaseDatos::conectar(':memory:');
}

function app(PDO $pdo): App
{
    return new App($pdo, __DIR__ . '/../vistas');
}

/** Datos de formulario con el token CSRF válido */
function form(array $datos): array
{
    return $datos + ['_token' => \Kanban\Csrf::token()];
}

// ---------- Repositorio de tableros ----------

function test_crear_tablero_con_columnas_iniciales(): void
{
    $t = new Tableros(bd());
    $id = $t->crear('  Mudanza  ', 'Cajas y papeleo');
    $tablero = $t->buscar($id);
    igual('Mudanza', $tablero['nombre'], 'nombre recortado:');
    $cols = $t->columnasConTarjetas($id);
    igual(Tableros::COLUMNAS_INICIALES, array_column($cols, 'nombre'), 'columnas:');
}

function test_validacion_de_tablero(): void
{
    $t = new Tableros(bd());
    $e = lanza(ErrorValidacion::class, fn () => $t->crear('   '));
    comprobar(isset($e->errores['nombre']));
    $e = lanza(ErrorValidacion::class, fn () => $t->crear(str_repeat('x', Tableros::MAX_NOMBRE + 1)));
    comprobar(isset($e->errores['nombre']));
    // Los caracteres multibyte cuentan como uno
    $t->crear(str_repeat('ñ', Tableros::MAX_NOMBRE));
}

function test_listar_cuenta_tarjetas(): void
{
    $pdo = bd();
    $t = new Tableros($pdo);
    $ta = new Tarjetas($pdo);
    $a = $t->crear('A');
    $b = $t->crear('B');
    $colA = $t->columnasConTarjetas($a)[0]['id'];
    $ta->crear((int) $colA, 'Uno');
    $ta->crear((int) $colA, 'Dos');
    $lista = $t->listar();
    igual([$b, $a], array_map('intval', array_column($lista, 'id')), 'orden (más reciente primero):');
    igual([0, 2], array_map('intval', array_column($lista, 'num_tarjetas')), 'tarjetas:');
}

function test_borrar_tablero_en_cascada(): void
{
    $pdo = bd();
    $t = new Tableros($pdo);
    $id = $t->crear('Temporal');
    $col = (int) $t->columnasConTarjetas($id)[0]['id'];
    (new Tarjetas($pdo))->crear($col, 'Se irá');
    comprobar($t->borrar($id));
    comprobar(!$t->borrar($id), 'borrar dos veces debe devolver false');
    igual(0, (int) $pdo->query('SELECT COUNT(*) FROM tarjetas')->fetchColumn(), 'tarjetas restantes:');
}

// ---------- Repositorio de tarjetas ----------

function test_tarjetas_se_ponen_al_final(): void
{
    $pdo = bd();
    $t = new Tableros($pdo);
    $ta = new Tarjetas($pdo);
    $id = $t->crear('Orden');
    $col = (int) $t->columnasConTarjetas($id)[1]['id'];
    $ta->crear($col, 'Primera');
    $ta->crear($col, 'Segunda');
    $ta->crear($col, 'Tercera', "línea 1\nlínea 2");
    $cols = $t->columnasConTarjetas($id);
    igual(['Primera', 'Segunda', 'Tercera'], array_column($cols[1]['tarjetas'], 'titulo'));
    igual([0, 1, 2], array_map('intval', array_column($cols[1]['tarjetas'], 'posicion')));
    igual([], $cols[0]['tarjetas'], 'otras columnas vacías:');
}

function test_validacion_de_tarjeta(): void
{
    $pdo = bd();
    $ta = new Tarjetas($pdo);
    $e = lanza(ErrorValidacion::class, fn () => $ta->crear(999, ''));
    comprobar(isset($e->errores['columna'], $e->errores['titulo']), 'debe acumular varios errores');
}

// ---------- Router ----------

function test_router_parametros_y_errores(): void
{
    $r = new Router();
    $r->get('/a/{id}/b/{otro}', fn (int $id, int $otro) => $id + $otro);
    igual(7, $r->despachar('GET', '/a/3/b/4?x=1'));
    igual(7, $r->despachar('GET', '/a/3/b/4/'), 'barra final:');
    igual(404, lanza(ErrorHttp::class, fn () => $r->despachar('GET', '/a/x/b/4'))->estado);
    igual(405, lanza(ErrorHttp::class, fn () => $r->despachar('POST', '/a/3/b/4'))->estado);
}

// ---------- App completa (peticiones simuladas) ----------

function test_flujo_completo_de_la_app(): void
{
    $pdo = bd();
    $app = app($pdo);

    $r = $app->manejar('GET', '/');
    igual(200, $r->estado);
    comprobar(str_contains($r->cuerpo, 'Todavía no tienes tableros'));

    // Crear tablero → redirección 303 a su página
    $r = $app->manejar('POST', '/tableros', form(['nombre' => 'Proyecto <web>']));
    igual(303, $r->estado);
    igual('/tableros/1', $r->cabeceras['Location']);

    // La página del tablero escapa el HTML y muestra el aviso una sola vez
    $r = $app->manejar('GET', '/tableros/1');
    comprobar(str_contains($r->cuerpo, 'Proyecto &lt;web&gt;'), 'el nombre debe ir escapado');
    comprobar(!str_contains($r->cuerpo, 'Proyecto <web>'));
    comprobar(str_contains($r->cuerpo, 'Tablero creado.'));
    comprobar(!str_contains($app->manejar('GET', '/tableros/1')->cuerpo, 'Tablero creado.'), 'aviso de un solo uso');

    // Añadir tarjeta a la primera columna
    $r = $app->manejar('POST', '/columnas/1/tarjetas', form(['titulo' => 'Maquetar portada']));
    igual(303, $r->estado);
    comprobar(str_contains($app->manejar('GET', '/tableros/1')->cuerpo, 'Maquetar portada'));

    // Portada con el contador
    comprobar(str_contains($app->manejar('GET', '/')->cuerpo, '1 tarjeta '));
}

function test_errores_de_formulario_y_http(): void
{
    $app = app(bd());
    $r = $app->manejar('POST', '/tableros', form(['nombre' => '']));
    igual(422, $r->estado);
    comprobar(str_contains($r->cuerpo, 'El nombre es obligatorio.'));

    $app->manejar('POST', '/tableros', form(['nombre' => 'X']));
    $r = $app->manejar('POST', '/columnas/1/tarjetas', form(['titulo' => ' ']));
    igual(422, $r->estado);
    comprobar(str_contains($r->cuerpo, 'El título es obligatorio.'));

    igual(404, $app->manejar('GET', '/tableros/99')->estado);
    igual(404, $app->manejar('GET', '/no-existe')->estado);
    igual(404, $app->manejar('POST', '/columnas/99/tarjetas', form(['titulo' => 'a']))->estado);
    igual(405, $app->manejar('GET', '/tableros')->estado);
}

function test_csrf_obligatorio_en_post(): void
{
    $app = app(bd());
    igual(419, $app->manejar('POST', '/tableros', ['nombre' => 'Sin token'])->estado);
    igual(419, $app->manejar('POST', '/tableros', ['nombre' => 'Malo', '_token' => 'abc'])->estado);
    comprobar(str_contains($app->manejar('GET', '/')->cuerpo, 'Todavía no tienes tableros'), 'no se debe haber creado nada');
}

function test_borrar_tablero_desde_la_app(): void
{
    $app = app(bd());
    $app->manejar('POST', '/tableros', form(['nombre' => 'Borrable']));
    $r = $app->manejar('POST', '/tableros/1/borrar', form([]));
    igual(303, $r->estado);
    igual(404, $app->manejar('GET', '/tableros/1')->estado);
    igual(404, $app->manejar('POST', '/tableros/1/borrar', form([]))->estado);
}

// ---------- Ejecución ----------

$tests = array_filter(get_defined_functions()['user'], fn ($f) => str_starts_with($f, 'test_'));
$fallos = 0;
foreach ($tests as $test) {
    $_SESSION = [];
    try {
        $test();
        echo "  ✔ $test\n";
    } catch (Throwable $e) {
        $fallos++;
        echo "  ✘ $test\n      " . $e::class . ': ' . $e->getMessage() . "\n";
    }
}
printf("\n%d tests, %d fallos\n", count($tests), $fallos);
exit($fallos ? 1 : 0);
