<?php
declare(strict_types=1);

// Mini runner de tests sin PHPUnit: php tests/ejecutar.php
// Cada función test_* se ejecuta con una base de datos SQLite en memoria nueva.

require __DIR__ . '/../src/autoload.php';

use Kanban\App;
use Kanban\BaseDatos;
use Kanban\Columnas;
use Kanban\ErrorHttp;
use Kanban\ErrorValidacion;
use Kanban\Estadisticas;
use Kanban\Exportador;
use Kanban\Filtro;
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

// ---------- Día 2: editar, borrar y mover tarjetas ----------

/** Tablero con 3 columnas; devuelve [pdo, tableroId, [idsColumnas]]. */
function tablero_de_prueba(): array
{
    $pdo = bd();
    $t = new Tableros($pdo);
    $id = $t->crear('Pruebas');
    return [$pdo, $id, array_map('intval', array_column($t->columnasConTarjetas($id), 'id'))];
}

/** Títulos por columna, p. ej. [['A','B'], [], ['C']], comprobando que las posiciones no tienen huecos. */
function titulos(PDO $pdo, int $tableroId): array
{
    $res = [];
    foreach ((new Tableros($pdo))->columnasConTarjetas($tableroId) as $col) {
        $pos = array_map('intval', array_column($col['tarjetas'], 'posicion'));
        igual($pos ? range(0, count($pos) - 1) : [], $pos, "posiciones de {$col['nombre']}:");
        $res[] = array_column($col['tarjetas'], 'titulo');
    }
    return $res;
}

function test_editar_tarjeta_con_etiqueta_y_fecha(): void
{
    [$pdo, , [$c1]] = tablero_de_prueba();
    $ta = new Tarjetas($pdo);
    $id = $ta->crear($c1, 'Original', '', 'rojo', '2026-12-01');
    $t = $ta->buscar($id);
    igual('rojo', $t['etiqueta']);
    igual('2026-12-01', $t['fecha_limite']);

    comprobar($ta->actualizar($id, ' Nuevo ', 'desc', 'verde', ''));
    $t = $ta->buscar($id);
    igual(['Nuevo', 'desc', 'verde', ''], [$t['titulo'], $t['descripcion'], $t['etiqueta'], $t['fecha_limite']]);

    $e = lanza(ErrorValidacion::class, fn () => $ta->actualizar($id, '', '', 'fucsia', '2026-02-30'));
    comprobar(isset($e->errores['titulo'], $e->errores['etiqueta'], $e->errores['fecha_limite']), 'tres errores a la vez');
    igual('Nuevo', $ta->buscar($id)['titulo'], 'no debe cambiar si falla:');
}

function test_borrar_tarjeta_cierra_el_hueco(): void
{
    [$pdo, $tab, [$c1]] = tablero_de_prueba();
    $ta = new Tarjetas($pdo);
    $ids = array_map(fn ($x) => $ta->crear($c1, $x), ['A', 'B', 'C']);
    comprobar($ta->borrar($ids[1]));
    comprobar(!$ta->borrar($ids[1]), 'ya no existe');
    igual([['A', 'C'], [], []], titulos($pdo, $tab));
}

function test_mover_entre_columnas_y_dentro_de_una(): void
{
    [$pdo, $tab, [$c1, $c2, $c3]] = tablero_de_prueba();
    $ta = new Tarjetas($pdo);
    [$a, $b, $c] = array_map(fn ($x) => $ta->crear($c1, $x), ['A', 'B', 'C']);
    $x = $ta->crear($c2, 'X');

    $ta->mover($b, $c2, 0);                 // B al principio de la columna 2
    igual([['A', 'C'], ['B', 'X'], []], titulos($pdo, $tab));
    $ta->mover($a, $c2, 99);                // posición fuera de rango → al final
    igual([['C'], ['B', 'X', 'A'], []], titulos($pdo, $tab));
    $ta->mover($a, $c2, 0);                 // reordenar dentro de la misma columna
    igual([['C'], ['A', 'B', 'X'], []], titulos($pdo, $tab));
    $ta->mover($a, $c2, 2);
    igual([['C'], ['B', 'X', 'A'], []], titulos($pdo, $tab));
    $ta->mover($x, $c3, -5);                // negativa → al principio
    igual([['C'], ['B', 'A'], ['X']], titulos($pdo, $tab));
}

function test_no_se_mueve_a_otro_tablero(): void
{
    [$pdo, $tab, [$c1]] = tablero_de_prueba();
    $otro = (new Tableros($pdo))->crear('Otro');
    $colOtro = (int) (new Tableros($pdo))->columnasConTarjetas($otro)[0]['id'];
    $ta = new Tarjetas($pdo);
    $id = $ta->crear($c1, 'Mía');
    lanza(ErrorValidacion::class, fn () => $ta->mover($id, $colOtro, 0));
    lanza(ErrorValidacion::class, fn () => $ta->mover($id, 999, 0));
    igual(404, lanza(ErrorHttp::class, fn () => $ta->mover(999, $c1, 0))->estado);
    igual([['Mía'], [], []], titulos($pdo, $tab));
}

function test_mover_con_botones(): void
{
    [$pdo, $tab, [$c1]] = tablero_de_prueba();
    $ta = new Tarjetas($pdo);
    [$a, $b] = array_map(fn ($x) => $ta->crear($c1, $x), ['A', 'B']);

    comprobar(!$ta->moverRelativo($a, 'arriba'), 'la primera no sube');
    comprobar($ta->moverRelativo($a, 'abajo'));
    igual([['B', 'A'], [], []], titulos($pdo, $tab));
    comprobar(!$ta->moverRelativo($a, 'abajo'), 'la última no baja');
    comprobar(!$ta->moverRelativo($a, 'izquierda'), 'no hay columna a la izquierda');
    comprobar($ta->moverRelativo($a, 'derecha'));
    comprobar($ta->moverRelativo($a, 'derecha'));
    comprobar(!$ta->moverRelativo($a, 'derecha'), 'no hay columna a la derecha');
    comprobar($ta->moverRelativo($b, 'derecha'));
    igual([[], ['B'], ['A']], titulos($pdo, $tab));
    lanza(ErrorValidacion::class, fn () => $ta->moverRelativo($a, 'diagonal'));
}

// ---------- Día 2: columnas ----------

function test_gestionar_columnas(): void
{
    [$pdo, $tab, [$c1, $c2, $c3]] = tablero_de_prueba();
    $cols = new Columnas($pdo);
    $nombres = fn () => array_column((new Tableros($pdo))->columnasConTarjetas($tab), 'nombre');

    $c4 = $cols->crear($tab, ' Revisión ');
    igual(['Por hacer', 'En curso', 'Hecho', 'Revisión'], $nombres());
    $cols->renombrar($c2, 'Haciendo');
    comprobar($cols->desplazar($c4, -1));
    igual(['Por hacer', 'Haciendo', 'Revisión', 'Hecho'], $nombres());
    comprobar(!$cols->desplazar($c1, -1), 'la primera no va más a la izquierda');

    (new Tarjetas($pdo))->crear($c2, 'Se borrará con la columna');
    $cols->borrar($c2);
    igual(['Por hacer', 'Revisión', 'Hecho'], $nombres());
    igual([0, 1, 2], array_map('intval', array_column((new Tableros($pdo))->columnasConTarjetas($tab), 'posicion')));
    igual(0, (int) $pdo->query('SELECT COUNT(*) FROM tarjetas')->fetchColumn(), 'tarjetas en cascada:');

    lanza(ErrorValidacion::class, fn () => $cols->renombrar($c1, '  '));
    lanza(ErrorValidacion::class, fn () => $cols->crear($tab, str_repeat('x', Columnas::MAX_NOMBRE + 1)));
    $cols->borrar($c4);
    $cols->borrar($c3);
    $e = lanza(ErrorValidacion::class, fn () => $cols->borrar($c1));
    comprobar(isset($e->errores['columna']), 'no se puede borrar la última');
}

function test_maximo_de_columnas(): void
{
    [$pdo, $tab] = tablero_de_prueba();
    $cols = new Columnas($pdo);
    for ($i = 3; $i < Columnas::MAX_POR_TABLERO; $i++) {
        $cols->crear($tab, "C$i");
    }
    lanza(ErrorValidacion::class, fn () => $cols->crear($tab, 'Una de más'));
}

// ---------- Día 2: fechas y migración ----------

function test_fechas(): void
{
    comprobar(fecha_valida('2026-11-24'));
    comprobar(fecha_valida('2028-02-29'), 'bisiesto');
    comprobar(!fecha_valida('2026-02-30'));
    comprobar(!fecha_valida('24/11/2026'));
    comprobar(!fecha_valida('2026-1-5'));
    igual('vencida', estado_fecha('2026-11-23', '2026-11-24'));
    igual('hoy', estado_fecha('2026-11-24', '2026-11-24'));
    igual('', estado_fecha('2026-11-25', '2026-11-24'));
    igual('', estado_fecha('', '2026-11-24'));
}

function test_migracion_de_base_antigua(): void
{
    // Base de datos con el esquema del día 1 (sin etiqueta ni fecha_limite)
    $ruta = sys_get_temp_dir() . '/kanban-migracion-' . getmypid() . '.sqlite';
    @unlink($ruta);
    $vieja = new PDO('sqlite:' . $ruta);
    $vieja->exec("CREATE TABLE tarjetas (id INTEGER PRIMARY KEY, columna_id INTEGER, titulo TEXT,
                  descripcion TEXT DEFAULT '', posicion INTEGER, creado_en TEXT)");
    $vieja->exec("INSERT INTO tarjetas VALUES (1, 1, 'Antigua', '', 0, '2026-11-23')");
    $vieja = null;

    $pdo = BaseDatos::conectar($ruta);
    $fila = $pdo->query('SELECT etiqueta, fecha_limite FROM tarjetas WHERE id = 1')->fetch();
    igual(['etiqueta' => '', 'fecha_limite' => ''], $fila);
    BaseDatos::conectar($ruta); // conectar otra vez no debe fallar
    $pdo = null;
    unlink($ruta);
}

// ---------- Día 2: rutas nuevas de la app ----------

function test_app_editar_y_borrar_tarjeta(): void
{
    $app = app(bd());
    $app->manejar('POST', '/tableros', form(['nombre' => 'T']));
    $app->manejar('POST', '/columnas/1/tarjetas', form(['titulo' => 'Vieja', 'etiqueta' => 'azul', 'fecha_limite' => '2000-01-01']));

    $tablero = $app->manejar('GET', '/tableros/1')->cuerpo;
    comprobar(str_contains($tablero, 'etiqueta-azul'), 'se pinta la etiqueta');
    comprobar(str_contains($tablero, 'fecha-vencida'), 'una fecha del año 2000 está vencida');

    $r = $app->manejar('GET', '/tarjetas/1/editar');
    igual(200, $r->estado);
    comprobar(str_contains($r->cuerpo, 'value="Vieja"'));
    comprobar(str_contains($r->cuerpo, '<option value="azul" selected>'));

    $r = $app->manejar('POST', '/tarjetas/1', form(['titulo' => '', 'fecha_limite' => 'mañana']));
    igual(422, $r->estado);
    comprobar(str_contains($r->cuerpo, 'El título es obligatorio.') && str_contains($r->cuerpo, 'AAAA-MM-DD'));

    $r = $app->manejar('POST', '/tarjetas/1', form(['titulo' => 'Nueva <b>', 'etiqueta' => '']));
    igual(303, $r->estado);
    $tablero = $app->manejar('GET', '/tableros/1')->cuerpo;
    comprobar(str_contains($tablero, 'Nueva &lt;b&gt;') && str_contains($tablero, 'Tarjeta guardada.'));
    comprobar(!str_contains($tablero, 'fecha-vencida'), 'se quitó la fecha');

    igual(303, $app->manejar('POST', '/tarjetas/1/borrar', form([]))->estado);
    igual(404, $app->manejar('GET', '/tarjetas/1/editar')->estado);
    igual(404, $app->manejar('POST', '/tarjetas/1/borrar', form([]))->estado);
}

function test_app_mover_con_botones_y_ajax(): void
{
    $pdo = bd();
    $app = app($pdo);
    $app->manejar('POST', '/tableros', form(['nombre' => 'T']));
    $app->manejar('POST', '/columnas/1/tarjetas', form(['titulo' => 'A']));
    $app->manejar('POST', '/columnas/1/tarjetas', form(['titulo' => 'B']));

    $r = $app->manejar('POST', '/tarjetas/1/mover', form(['direccion' => 'derecha']));
    igual(303, $r->estado);
    igual('/tableros/1#tarjeta-1', $r->cabeceras['Location']);
    igual([['B'], ['A'], []], titulos($pdo, 1));

    // Arrastrar y soltar: responde JSON
    $r = $app->manejar('POST', '/tarjetas/2/mover', form(['ajax' => '1', 'columna_id' => '2', 'posicion' => '0']));
    igual(200, $r->estado);
    igual('application/json; charset=utf-8', $r->cabeceras['Content-Type']);
    igual(['ok' => true], json_decode($r->cuerpo, true));
    igual([[], ['B', 'A'], []], titulos($pdo, 1));

    $r = $app->manejar('POST', '/tarjetas/2/mover', form(['ajax' => '1', 'columna_id' => '99', 'posicion' => '0']));
    igual(422, $r->estado);
    igual(false, json_decode($r->cuerpo, true)['ok']);
    $r = $app->manejar('POST', '/tarjetas/99/mover', form(['ajax' => '1', 'columna_id' => '1']));
    igual(404, $r->estado);
    comprobar(str_starts_with($r->cuerpo, '{'), 'los errores AJAX también van en JSON');
    igual(419, $app->manejar('POST', '/tarjetas/2/mover', ['ajax' => '1'])->estado);
}

function test_app_columnas(): void
{
    $pdo = bd();
    $app = app($pdo);
    $app->manejar('POST', '/tableros', form(['nombre' => 'T']));
    $app->manejar('GET', '/tableros/1'); // consume el aviso de creación

    igual(303, $app->manejar('POST', '/tableros/1/columnas', form(['nombre' => 'Bloqueado']))->estado);
    igual(303, $app->manejar('POST', '/columnas/2', form(['nombre' => 'Haciendo']))->estado);
    igual(303, $app->manejar('POST', '/columnas/4/mover', form(['direccion' => 'izquierda']))->estado);
    $html = $app->manejar('GET', '/tableros/1')->cuerpo;
    comprobar(strpos($html, 'Haciendo') < strpos($html, 'Bloqueado') && strpos($html, 'Bloqueado') < strpos($html, '>Hecho'), 'orden de columnas');

    // Error de validación → aviso de error en el tablero
    $app->manejar('POST', '/columnas/2', form(['nombre' => '']));
    $html = $app->manejar('GET', '/tableros/1')->cuerpo;
    comprobar(str_contains($html, 'aviso-error') && str_contains($html, 'obligatorio'));

    igual(303, $app->manejar('POST', '/columnas/2/borrar', form([]))->estado);
    igual(3, (new Columnas($pdo))->contar(1));
    igual(404, $app->manejar('POST', '/columnas/2/borrar', form([]))->estado);
    igual(404, $app->manejar('POST', '/tableros/9/columnas', form(['nombre' => 'x']))->estado);
}


// ---------- Día 3: filtros, estadísticas, exportación y API ----------

/** Tarjeta mínima para probar clases puras sin BD */
function tj(string $titulo, string $etiqueta = '', string $fecha = '', string $desc = ''): array
{
    return ['id' => 1, 'titulo' => $titulo, 'descripcion' => $desc, 'etiqueta' => $etiqueta,
            'fecha_limite' => $fecha, 'creado_en' => '2026-11-25T10:00:00+01:00'];
}

function test_normalizar_y_url(): void
{
    igual('cafe con nino', normalizar('CAFÉ con Niño'));
    igual('cancion', normalizar('CANCIÓN'));
    igual('/t/1?q=a+b&estado=hoy', url('/t/1', ['q' => 'a b', 'estado' => 'hoy']));
    igual('/t/1', url('/t/1'));
}

function test_filtro_desde_consulta_ignora_valores_raros(): void
{
    $f = Filtro::desdeConsulta(['q' => '  hola ', 'etiqueta' => 'fucsia', 'estado' => 'DROP TABLE']);
    igual('hola', $f->texto);
    igual('', $f->etiqueta);
    igual('', $f->estado);
    comprobar($f->activo());
    comprobar(!Filtro::desdeConsulta([])->activo());
    // Un array en vez de texto (?q[]=x) no debe romper nada
    igual('', Filtro::desdeConsulta(['q' => ['x'], 'estado' => ['hoy']])->texto);
    igual(100, mb_strlen(Filtro::desdeConsulta(['q' => str_repeat('á', 300)])->texto));
    igual(['q' => 'hola'], $f->aConsulta());
}

function test_filtro_texto_etiqueta_y_fechas(): void
{
    $hoy = '2026-11-25';
    $busca = fn (array $c, array $t) => Filtro::desdeConsulta($c)->coincide($t, $hoy);
    $cafe = tj('Comprar café', 'rojo', '2026-11-20', 'Para la oficina');

    comprobar($busca(['q' => 'CAFE'], $cafe), 'sin tildes ni mayúsculas');
    comprobar($busca(['q' => 'oficina comprar'], $cafe), 'palabras en cualquier orden, también en la descripción');
    comprobar(!$busca(['q' => 'café té'], $cafe), 'todas las palabras deben estar');
    comprobar($busca(['etiqueta' => 'rojo'], $cafe));
    comprobar(!$busca(['etiqueta' => 'azul'], $cafe));
    comprobar($busca(['estado' => 'vencidas'], $cafe));
    comprobar(!$busca(['estado' => 'hoy'], $cafe));
    comprobar($busca(['estado' => 'hoy'], tj('x', '', $hoy)));
    comprobar($busca(['estado' => 'sin_fecha'], tj('x')));
    comprobar(!$busca(['estado' => 'con_fecha'], tj('x')));
    comprobar(!$busca(['q' => 'café', 'etiqueta' => 'azul'], $cafe), 'condiciones combinadas con Y');

    $cols = [['nombre' => 'A', 'tarjetas' => [$cafe, tj('Otra')]], ['nombre' => 'B', 'tarjetas' => [tj('Café 2')]]];
    $res = Filtro::desdeConsulta(['q' => 'cafe'])->aplicar($cols, $hoy);
    igual([['Comprar café'], ['Café 2']], array_map(fn ($c) => array_column($c['tarjetas'], 'titulo'), $res));
    igual($cols, Filtro::desdeConsulta([])->aplicar($cols), 'sin filtro no cambia nada');
}

function test_estadisticas(): void
{
    $hoy = '2026-11-25';
    $cols = [
        ['nombre' => 'Por hacer', 'tarjetas' => [tj('a', 'rojo', '2026-11-01'), tj('b', '', $hoy), tj('c', 'rojo', '2026-12-24')]],
        ['nombre' => 'En curso', 'tarjetas' => [tj('d', 'azul', '2026-12-01')]],
        ['nombre' => 'Hecho', 'tarjetas' => [tj('e', '', '2026-01-01'), tj('f'), tj('g'), tj('h')]],
    ];
    $e = Estadisticas::calcular($cols, $hoy);
    igual(8, $e['total']);
    igual(4, $e['hechas']);
    igual(50, $e['progreso']);
    igual([3, 1, 4], array_column($e['por_columna'], 'tarjetas'));
    igual(2, $e['por_etiqueta']['rojo']);
    igual(5, $e['por_etiqueta']['']);
    igual(5, $e['con_fecha']);
    igual(1, $e['vencidas'], 'la vencida de "Hecho" no cuenta:');
    igual(1, $e['vencen_hoy']);
    igual(['d', 'c'], array_column($e['proximas'], 'titulo'), 'próximas ordenadas por fecha:');

    $vacio = Estadisticas::calcular([]);
    igual(0, $vacio['total']);
    igual(0, $vacio['progreso'], 'sin división entre cero');
}

function test_exportar_csv_escapa_y_evita_formulas(): void
{
    $cols = [['nombre' => 'Por hacer', 'tarjetas' => [
        tj('Hola, "mundo"', 'verde', '', "dos\nlíneas"),
        tj('=HYPERLINK("http://malo")'),
    ]]];
    $csv = Exportador::csv($cols);
    comprobar(str_starts_with($csv, "\xEF\xBB\xBF"), 'BOM para Excel');
    $f = fopen('php://temp', 'r+');
    fwrite($f, substr($csv, 3));
    rewind($f);
    $filas = [];
    while (($fila = fgetcsv($f, null, ',', '"', '')) !== false) {
        $filas[] = $fila;
    }
    igual(Exportador::CABECERA_CSV, $filas[0]);
    igual(3, count($filas), 'cabecera + 2 tarjetas (el salto de línea va dentro de comillas)');
    igual('Hola, "mundo"', $filas[1][2]);
    igual("dos\nlíneas", $filas[1][3]);
    igual('1', $filas[1][1], 'posición empezando en 1');
    igual("'=HYPERLINK(\"http://malo\")", $filas[2][2], 'fórmula neutralizada');
    igual('texto', Exportador::celdaSegura('texto'));
    igual("'@SUM(A1)", Exportador::celdaSegura('@SUM(A1)'));
    igual('mi-tablero-ano-2026.csv', Exportador::nombreFichero('¡Mi tablero (año 2026)!', 'csv'));
    igual('tablero.json', Exportador::nombreFichero('###', 'json'));
}

/** Tablero con tarjetas variadas creado a través de la app */
function app_con_datos(): array
{
    $pdo = bd();
    $app = app($pdo);
    $app->manejar('POST', '/tableros', form(['nombre' => 'Viaje']));
    $app->manejar('POST', '/columnas/1/tarjetas', form(['titulo' => 'Reservar hotel', 'etiqueta' => 'rojo', 'fecha_limite' => '2020-01-01']));
    $app->manejar('POST', '/columnas/1/tarjetas', form(['titulo' => 'Comprar maleta', 'descripcion' => 'Una pequeña']));
    $app->manejar('POST', '/columnas/3/tarjetas', form(['titulo' => 'Pedir vacaciones', 'etiqueta' => 'verde']));
    $app->manejar('GET', '/tableros/1'); // consume el aviso
    return [$pdo, $app];
}

function test_app_tablero_con_filtros(): void
{
    [, $app] = app_con_datos();
    $html = $app->manejar('GET', '/tableros/1')->cuerpo;
    comprobar(str_contains($html, 'draggable="true"'), 'sin filtros se puede arrastrar');

    $r = $app->manejar('GET', '/tableros/1?q=MALETA');
    igual(200, $r->estado);
    comprobar(str_contains($r->cuerpo, 'Comprar maleta'));
    comprobar(!str_contains($r->cuerpo, 'Reservar hotel'));
    comprobar(str_contains($r->cuerpo, 'Mostrando <strong>1</strong> de 3 tarjetas'));
    comprobar(!str_contains($r->cuerpo, 'draggable="true"'), 'con filtros no se arrastra');
    comprobar(str_contains($r->cuerpo, 'value="MALETA"'), 'el buscador conserva el texto');
    comprobar(str_contains($r->cuerpo, '/exportar/csv?q=MALETA'), 'exportar respeta el filtro');

    $html = $app->manejar('GET', '/tableros/1?estado=vencidas')->cuerpo;
    comprobar(str_contains($html, 'Reservar hotel') && !str_contains($html, 'Comprar maleta'));
    $html = $app->manejar('GET', '/tableros/1?etiqueta=verde')->cuerpo;
    comprobar(str_contains($html, 'Pedir vacaciones') && !str_contains($html, 'Reservar hotel'));

    // El texto buscado se escapa al pintarlo
    $html = $app->manejar('GET', '/tableros/1?q=' . urlencode('"><script>'))->cuerpo;
    comprobar(!str_contains($html, '"><script>') && str_contains($html, '&quot;&gt;&lt;script&gt;'));
}

function test_app_api_json(): void
{
    [, $app] = app_con_datos();
    $r = $app->manejar('GET', '/api/tableros');
    igual(200, $r->estado);
    igual('application/json; charset=utf-8', $r->cabeceras['Content-Type']);
    $lista = json_decode($r->cuerpo, true)['tableros'];
    igual([['id' => 1, 'nombre' => 'Viaje', 'descripcion' => '', 'num_tarjetas' => 3, 'url' => '/api/tableros/1']], $lista);

    $d = json_decode($app->manejar('GET', '/api/tableros/1')->cuerpo, true);
    igual('Viaje', $d['nombre']);
    igual(['Por hacer', 'En curso', 'Hecho'], array_column($d['columnas'], 'nombre'));
    igual(null, $d['columnas'][0]['tarjetas'][1]['etiqueta'], 'campos vacíos como null');
    igual('rojo', $d['columnas'][0]['tarjetas'][0]['etiqueta']);
    igual(3, $d['estadisticas']['total']);
    igual(33, $d['estadisticas']['progreso']);
    igual([], $d['filtro']);

    $d = json_decode($app->manejar('GET', '/api/tableros/1?etiqueta=rojo')->cuerpo, true);
    igual(['etiqueta' => 'rojo'], $d['filtro']);
    igual([1, 0, 0], array_map(fn ($c) => count($c['tarjetas']), $d['columnas']));
    igual(3, $d['estadisticas']['total'], 'las estadísticas son de todo el tablero');

    // Errores de la API también en JSON
    $r = $app->manejar('GET', '/api/tableros/99');
    igual(404, $r->estado);
    igual(['ok' => false, 'error' => 'Ese tablero no existe'], json_decode($r->cuerpo, true));
    igual(405, $app->manejar('POST', '/api/tableros', form([]))->estado);
    $r = $app->manejar('GET', '/api/nada');
    igual(404, $r->estado);
    igual(false, json_decode($r->cuerpo, true)['ok']);
}

function test_app_exportar_y_estadisticas(): void
{
    [, $app] = app_con_datos();
    $r = $app->manejar('GET', '/tableros/1/exportar/csv');
    igual(200, $r->estado);
    igual('attachment; filename="viaje.csv"', $r->cabeceras['Content-Disposition']);
    igual(4, substr_count(trim($r->cuerpo), "\n") + 1, 'cabecera + 3 tarjetas');

    $r = $app->manejar('GET', '/tableros/1/exportar/csv?q=maleta');
    igual(2, substr_count(trim($r->cuerpo), "\n") + 1, 'solo la tarjeta filtrada');

    $r = $app->manejar('GET', '/tableros/1/exportar/json');
    igual('attachment; filename="viaje.json"', $r->cabeceras['Content-Disposition']);
    igual('Pedir vacaciones', json_decode($r->cuerpo, true)['columnas'][2]['tarjetas'][0]['titulo']);

    $html = $app->manejar('GET', '/tableros/1/estadisticas')->cuerpo;
    comprobar(str_contains($html, 'Estadísticas de «Viaje»'));
    comprobar(str_contains($html, '33 %'));
    comprobar(str_contains($html, '?estado=vencidas'), 'enlace a las vencidas');
    igual(404, $app->manejar('GET', '/tableros/9/estadisticas')->estado);
    igual(404, $app->manejar('GET', '/tableros/9/exportar/csv')->estado);

    // Tablero vacío
    $app->manejar('POST', '/tableros', form(['nombre' => 'Vacío']));
    comprobar(str_contains($app->manejar('GET', '/tableros/2/estadisticas')->cuerpo, 'todavía no tiene tarjetas'));
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
