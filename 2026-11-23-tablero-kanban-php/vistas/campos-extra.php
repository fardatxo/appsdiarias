<?php
/** Campos de etiqueta y fecha límite, compartidos por "nueva tarjeta" y "editar tarjeta". */
$valores = $valores ?? [];
$errores = $errores ?? [];
$etiquetaActual = $valores['etiqueta'] ?? '';
?>
<div class="campos-extra">
    <label>Etiqueta
        <select name="etiqueta">
            <option value="">Sin etiqueta</option>
            <?php foreach (\Kanban\Tarjetas::ETIQUETAS as $clave => $nombre): ?>
                <option value="<?= e($clave) ?>" <?= $clave === $etiquetaActual ? 'selected' : '' ?>><?= e($nombre) ?></option>
            <?php endforeach ?>
        </select>
    </label>
    <label>Fecha límite
        <input type="date" name="fecha_limite" value="<?= e($valores['fecha_limite'] ?? '') ?>">
    </label>
</div>
<?php if (isset($errores['etiqueta'])): ?><p class="error"><?= e($errores['etiqueta']) ?></p><?php endif ?>
<?php if (isset($errores['fecha_limite'])): ?><p class="error"><?= e($errores['fecha_limite']) ?></p><?php endif ?>
