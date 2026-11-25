<?php
/** Estadísticas de un tablero: progreso, tarjetas por columna y etiqueta, fechas. */
$tid = (int) $tablero['id'];
$max = max(1, ...array_column($est['por_columna'], 'tarjetas'));
$maxEtiqueta = max(1, ...array_values($est['por_etiqueta']));
?>
<p><a href="/tableros/<?= $tid ?>">← Volver al tablero</a></p>
<h1>Estadísticas de «<?= e($tablero['nombre']) ?>»</h1>

<?php if ($est['total'] === 0): ?>
    <p class="vacio">Este tablero todavía no tiene tarjetas.</p>
<?php else: ?>
<div class="cifras">
    <div class="cifra"><span><?= $est['total'] ?></span>tarjetas</div>
    <div class="cifra"><span><?= $est['progreso'] ?> %</span>en «<?= e($est['por_columna'][array_key_last($est['por_columna'])]['nombre']) ?>»</div>
    <div class="cifra <?= $est['vencidas'] ? 'cifra-mal' : '' ?>"><span><?= $est['vencidas'] ?></span>vencidas</div>
    <div class="cifra"><span><?= $est['vencen_hoy'] ?></span>vencen hoy</div>
</div>

<div class="progreso" role="progressbar" aria-valuenow="<?= $est['progreso'] ?>" aria-valuemin="0" aria-valuemax="100">
    <div style="width: <?= $est['progreso'] ?>%"></div>
</div>

<div class="paneles">
    <section class="tarjeta-form">
        <h2>Por columna</h2>
        <?php foreach ($est['por_columna'] as $c): ?>
            <div class="barra-fila">
                <span class="barra-nombre"><?= e($c['nombre']) ?></span>
                <span class="barra"><span style="width: <?= round($c['tarjetas'] * 100 / $max) ?>%"></span></span>
                <span class="barra-num"><?= $c['tarjetas'] ?></span>
            </div>
        <?php endforeach ?>
    </section>

    <section class="tarjeta-form">
        <h2>Por etiqueta</h2>
        <?php foreach ($est['por_etiqueta'] as $clave => $n): ?>
            <div class="barra-fila">
                <span class="barra-nombre"><?= e($clave === '' ? 'Sin etiqueta' : \Kanban\Tarjetas::ETIQUETAS[$clave]) ?></span>
                <span class="barra"><span class="<?= $clave !== '' ? 'etiqueta-' . e($clave) : '' ?>" style="width: <?= round($n * 100 / $maxEtiqueta) ?>%"></span></span>
                <span class="barra-num"><?= $n ?></span>
            </div>
        <?php endforeach ?>
    </section>

    <section class="tarjeta-form">
        <h2>Próximas fechas límite</h2>
        <?php if (!$est['proximas']): ?>
            <p class="vacio">No hay tarjetas pendientes con fecha futura.</p>
        <?php else: ?>
            <ul class="proximas">
                <?php foreach ($est['proximas'] as $p): ?>
                    <li><strong><?= fecha_corta($p['fecha_limite']) ?></strong> · <?= e($p['titulo']) ?> <span class="desc">(<?= e($p['columna']) ?>)</span></li>
                <?php endforeach ?>
            </ul>
        <?php endif ?>
        <p class="ayuda"><?= plural($est['con_fecha'], 'tarjeta tiene', 'tarjetas tienen') ?> fecha límite. Las de la última columna no cuentan como vencidas.</p>
        <?php if ($est['vencidas']): ?>
            <p><a href="/tableros/<?= $tid ?>?estado=vencidas">Ver las vencidas en el tablero →</a></p>
        <?php endif ?>
    </section>
</div>
<?php endif ?>
