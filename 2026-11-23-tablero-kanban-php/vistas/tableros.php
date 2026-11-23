<?php
/** Portada: lista de tableros y formulario de creación. */
$errores = $errores ?? [];
$viejo = $viejo ?? [];
?>
<h1>Mis tableros</h1>

<section class="tarjeta-form">
    <h2>Nuevo tablero</h2>
    <form method="post" action="/tableros" class="formulario">
        <?= \Kanban\Csrf::campo() ?>
        <label>Nombre
            <input name="nombre" maxlength="<?= \Kanban\Tableros::MAX_NOMBRE ?>" required
                   value="<?= e($viejo['nombre'] ?? '') ?>" placeholder="p. ej. Mudanza, TFG, Proyecto web">
        </label>
        <?php if (isset($errores['nombre'])): ?><p class="error"><?= e($errores['nombre']) ?></p><?php endif ?>
        <label>Descripción (opcional)
            <textarea name="descripcion" rows="2" maxlength="<?= \Kanban\Tableros::MAX_DESCRIPCION ?>"><?= e($viejo['descripcion'] ?? '') ?></textarea>
        </label>
        <?php if (isset($errores['descripcion'])): ?><p class="error"><?= e($errores['descripcion']) ?></p><?php endif ?>
        <button type="submit">Crear tablero</button>
    </form>
</section>

<?php if (!$tableros): ?>
    <p class="vacio">Todavía no tienes tableros. Crea el primero arriba.</p>
<?php else: ?>
    <ul class="rejilla-tableros">
        <?php foreach ($tableros as $t): ?>
            <li class="tablero-mini">
                <a href="/tableros/<?= (int) $t['id'] ?>">
                    <strong><?= e($t['nombre']) ?></strong>
                    <?php if ($t['descripcion'] !== ''): ?><span class="desc"><?= e($t['descripcion']) ?></span><?php endif ?>
                    <span class="meta"><?= plural((int) $t['num_tarjetas'], 'tarjeta', 'tarjetas') ?> · creado el <?= fecha_corta($t['creado_en']) ?></span>
                </a>
            </li>
        <?php endforeach ?>
    </ul>
<?php endif ?>
