<?php
/** Vista de un tablero: columnas en horizontal con sus tarjetas. */
$erroresPorColumna = $erroresPorColumna ?? [];
$viejoPorColumna = $viejoPorColumna ?? [];
$numColumnas = count($columnas);
$hoy = date('Y-m-d');
?>
<div class="titulo-tablero">
    <div>
        <h1><?= e($tablero['nombre']) ?></h1>
        <?php if ($tablero['descripcion'] !== ''): ?><p class="desc"><?= e($tablero['descripcion']) ?></p><?php endif ?>
    </div>
    <form method="post" action="/tableros/<?= (int) $tablero['id'] ?>/borrar"
          onsubmit="return confirm('¿Borrar el tablero y todas sus tarjetas?')">
        <?= \Kanban\Csrf::campo() ?>
        <button type="submit" class="peligro">Borrar tablero</button>
    </form>
</div>

<p class="ayuda">Arrastra las tarjetas para moverlas o usa los botones ← ↑ ↓ →.</p>

<div class="columnas">
    <?php foreach ($columnas as $i => $col): ?>
        <?php
        $colId = (int) $col['id'];
        $err = $erroresPorColumna[$colId] ?? [];
        $viejo = $viejoPorColumna[$colId] ?? [];
        $numTarjetas = count($col['tarjetas']);
        ?>
        <section class="columna" id="col-<?= $colId ?>">
            <header class="cabecera-columna">
                <h2><?= e($col['nombre']) ?> <span class="contador"><?= $numTarjetas ?></span></h2>
                <details class="menu-columna">
                    <summary title="Opciones de la columna">⋯</summary>
                    <div class="menu">
                        <form method="post" action="/columnas/<?= $colId ?>" class="en-linea">
                            <?= \Kanban\Csrf::campo() ?>
                            <input name="nombre" value="<?= e($col['nombre']) ?>" required
                                   maxlength="<?= \Kanban\Columnas::MAX_NOMBRE ?>" aria-label="Nuevo nombre">
                            <button type="submit">Renombrar</button>
                        </form>
                        <form method="post" action="/columnas/<?= $colId ?>/mover" class="en-linea">
                            <?= \Kanban\Csrf::campo() ?>
                            <button name="direccion" value="izquierda" class="secundario" <?= $i === 0 ? 'disabled' : '' ?>>← Mover</button>
                            <button name="direccion" value="derecha" class="secundario" <?= $i === $numColumnas - 1 ? 'disabled' : '' ?>>Mover →</button>
                        </form>
                        <form method="post" action="/columnas/<?= $colId ?>/borrar"
                              onsubmit="return confirm('¿Borrar la columna y sus <?= $numTarjetas ?> tarjetas?')">
                            <?= \Kanban\Csrf::campo() ?>
                            <button type="submit" class="peligro" <?= $numColumnas <= 1 ? 'disabled' : '' ?>>Borrar columna</button>
                        </form>
                    </div>
                </details>
            </header>

            <ul class="lista-tarjetas" data-columna="<?= $colId ?>">
                <?php foreach ($col['tarjetas'] as $j => $tarjeta): ?>
                    <?php
                    $id = (int) $tarjeta['id'];
                    $estadoFecha = estado_fecha($tarjeta['fecha_limite'], $hoy);
                    $etiqueta = $tarjeta['etiqueta'];
                    ?>
                    <li class="tarjeta <?= $estadoFecha ? 'fecha-' . $estadoFecha : '' ?>" id="tarjeta-<?= $id ?>"
                        draggable="true" data-id="<?= $id ?>">
                        <?php if ($etiqueta !== '' && isset(\Kanban\Tarjetas::ETIQUETAS[$etiqueta])): ?>
                            <span class="etiqueta etiqueta-<?= e($etiqueta) ?>"><?= e(\Kanban\Tarjetas::ETIQUETAS[$etiqueta]) ?></span>
                        <?php endif ?>
                        <strong><?= e($tarjeta['titulo']) ?></strong>
                        <?php if ($tarjeta['descripcion'] !== ''): ?>
                            <p><?= nl2br(e($tarjeta['descripcion'])) ?></p>
                        <?php endif ?>
                        <?php if ($tarjeta['fecha_limite'] !== ''): ?>
                            <span class="fecha">
                                📅 <?= fecha_corta($tarjeta['fecha_limite']) ?>
                                <?= $estadoFecha === 'vencida' ? '· vencida' : ($estadoFecha === 'hoy' ? '· vence hoy' : '') ?>
                            </span>
                        <?php endif ?>
                        <form method="post" action="/tarjetas/<?= $id ?>/mover" class="acciones-tarjeta">
                            <?= \Kanban\Csrf::campo() ?>
                            <button name="direccion" value="izquierda" title="A la columna anterior" <?= $i === 0 ? 'disabled' : '' ?>>←</button>
                            <button name="direccion" value="arriba" title="Subir" <?= $j === 0 ? 'disabled' : '' ?>>↑</button>
                            <button name="direccion" value="abajo" title="Bajar" <?= $j === $numTarjetas - 1 ? 'disabled' : '' ?>>↓</button>
                            <button name="direccion" value="derecha" title="A la columna siguiente" <?= $i === $numColumnas - 1 ? 'disabled' : '' ?>>→</button>
                            <a href="/tarjetas/<?= $id ?>/editar" class="editar">Editar</a>
                        </form>
                    </li>
                <?php endforeach ?>
            </ul>

            <details class="nueva-tarjeta" <?= $err ? 'open' : '' ?>>
                <summary>+ Añadir tarjeta</summary>
                <form method="post" action="/columnas/<?= $colId ?>/tarjetas" class="formulario">
                    <?= \Kanban\Csrf::campo() ?>
                    <input name="titulo" placeholder="Título" required maxlength="<?= \Kanban\Tarjetas::MAX_TITULO ?>"
                           value="<?= e($viejo['titulo'] ?? '') ?>">
                    <?php if (isset($err['titulo'])): ?><p class="error"><?= e($err['titulo']) ?></p><?php endif ?>
                    <textarea name="descripcion" rows="2" placeholder="Descripción (opcional)"><?= e($viejo['descripcion'] ?? '') ?></textarea>
                    <?php if (isset($err['descripcion'])): ?><p class="error"><?= e($err['descripcion']) ?></p><?php endif ?>
                    <?= $this->parcial('campos-extra', ['valores' => $viejo, 'errores' => $err]) ?>
                    <button type="submit">Añadir</button>
                </form>
            </details>
        </section>
    <?php endforeach ?>

    <?php if ($numColumnas < \Kanban\Columnas::MAX_POR_TABLERO): ?>
        <section class="columna columna-nueva">
            <form method="post" action="/tableros/<?= (int) $tablero['id'] ?>/columnas" class="formulario">
                <?= \Kanban\Csrf::campo() ?>
                <input name="nombre" placeholder="Nueva columna" required maxlength="<?= \Kanban\Columnas::MAX_NOMBRE ?>">
                <button type="submit">+ Añadir columna</button>
            </form>
        </section>
    <?php endif ?>
</div>
