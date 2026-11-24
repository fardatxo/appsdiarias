<?php /** @var string $titulo  @var string $contenido */ ?>
<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title><?= e($titulo) ?> · Kanban PHP</title>
    <meta name="csrf" content="<?= e(\Kanban\Csrf::token()) ?>">
    <link rel="stylesheet" href="/estilos.css">
    <script src="/app.js" defer></script>
</head>
<body>
<header class="cabecera">
    <a href="/" class="logo">▦ Kanban PHP</a>
    <nav><a href="/">Mis tableros</a></nav>
</header>
<main class="contenedor">
    <?php if (!empty($aviso)): ?>
        <p class="aviso <?= ($aviso['tipo'] ?? 'ok') === 'error' ? 'aviso-error' : '' ?>" role="status"><?= e($aviso['texto'] ?? '') ?></p>
    <?php endif ?>
    <?= $contenido /* ya viene escapado desde la vista */ ?>
</main>
</body>
</html>
