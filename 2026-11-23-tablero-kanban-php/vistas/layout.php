<?php /** @var string $titulo  @var string $contenido */ ?>
<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title><?= e($titulo) ?> · Kanban PHP</title>
    <link rel="stylesheet" href="/estilos.css">
</head>
<body>
<header class="cabecera">
    <a href="/" class="logo">▦ Kanban PHP</a>
    <nav><a href="/">Mis tableros</a></nav>
</header>
<main class="contenedor">
    <?php if (!empty($aviso)): ?>
        <p class="aviso" role="status"><?= e($aviso) ?></p>
    <?php endif ?>
    <?= $contenido /* ya viene escapado desde la vista */ ?>
</main>
</body>
</html>
