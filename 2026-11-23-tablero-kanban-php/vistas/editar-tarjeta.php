<?php
/** Formulario para editar o borrar una tarjeta. */
$errores = $errores ?? [];
$volver = '/tableros/' . (int) $tarjeta['tablero_id'];
?>
<p><a href="<?= $volver ?>">← Volver a «<?= e($tablero['nombre'] ?? 'tablero') ?>»</a></p>

<section class="tarjeta-form">
    <h1>Editar tarjeta</h1>
    <form method="post" action="/tarjetas/<?= (int) $tarjeta['id'] ?>" class="formulario">
        <?= \Kanban\Csrf::campo() ?>
        <label>Título
            <input name="titulo" required maxlength="<?= \Kanban\Tarjetas::MAX_TITULO ?>" value="<?= e($tarjeta['titulo']) ?>">
        </label>
        <?php if (isset($errores['titulo'])): ?><p class="error"><?= e($errores['titulo']) ?></p><?php endif ?>
        <label>Descripción
            <textarea name="descripcion" rows="5" maxlength="<?= \Kanban\Tarjetas::MAX_DESCRIPCION ?>"><?= e($tarjeta['descripcion']) ?></textarea>
        </label>
        <?php if (isset($errores['descripcion'])): ?><p class="error"><?= e($errores['descripcion']) ?></p><?php endif ?>
        <?= $this->parcial('campos-extra', ['valores' => $tarjeta, 'errores' => $errores]) ?>
        <div class="botones">
            <button type="submit">Guardar</button>
            <a href="<?= $volver ?>">Cancelar</a>
        </div>
    </form>
</section>

<form method="post" action="/tarjetas/<?= (int) $tarjeta['id'] ?>/borrar"
      onsubmit="return confirm('¿Borrar esta tarjeta?')">
    <?= \Kanban\Csrf::campo() ?>
    <button type="submit" class="peligro">Borrar tarjeta</button>
</form>
