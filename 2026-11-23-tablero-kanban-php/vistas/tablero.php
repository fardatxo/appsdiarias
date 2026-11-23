<?php
/** Vista de un tablero: columnas en horizontal con sus tarjetas. */
$erroresPorColumna = $erroresPorColumna ?? [];
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

<div class="columnas">
    <?php foreach ($columnas as $col): ?>
        <?php $err = $erroresPorColumna[(int) $col['id']] ?? []; ?>
        <section class="columna">
            <h2><?= e($col['nombre']) ?> <span class="contador"><?= count($col['tarjetas']) ?></span></h2>

            <ul class="lista-tarjetas">
                <?php foreach ($col['tarjetas'] as $tarjeta): ?>
                    <li class="tarjeta">
                        <strong><?= e($tarjeta['titulo']) ?></strong>
                        <?php if ($tarjeta['descripcion'] !== ''): ?>
                            <p><?= nl2br(e($tarjeta['descripcion'])) ?></p>
                        <?php endif ?>
                    </li>
                <?php endforeach ?>
            </ul>

            <details class="nueva-tarjeta" <?= $err ? 'open' : '' ?>>
                <summary>+ Añadir tarjeta</summary>
                <form method="post" action="/columnas/<?= (int) $col['id'] ?>/tarjetas" class="formulario">
                    <?= \Kanban\Csrf::campo() ?>
                    <input name="titulo" placeholder="Título" required maxlength="<?= \Kanban\Tarjetas::MAX_TITULO ?>">
                    <?php if (isset($err['titulo'])): ?><p class="error"><?= e($err['titulo']) ?></p><?php endif ?>
                    <textarea name="descripcion" rows="2" placeholder="Descripción (opcional)"></textarea>
                    <?php if (isset($err['descripcion'])): ?><p class="error"><?= e($err['descripcion']) ?></p><?php endif ?>
                    <button type="submit">Añadir</button>
                </form>
            </details>
        </section>
    <?php endforeach ?>
</div>
