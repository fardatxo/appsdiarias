<?php
declare(strict_types=1);

// Funciones globales usadas por las plantillas de vistas/

/** Escapa texto para HTML. Todo lo que viene del usuario pasa por aquí. */
function e(mixed $valor): string
{
    return htmlspecialchars((string) $valor, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

/** "3 tarjetas" / "1 tarjeta" */
function plural(int $n, string $singular, string $plural): string
{
    return $n . ' ' . ($n === 1 ? $singular : $plural);
}

/** Fecha ISO → "23/11/2026" */
function fecha_corta(string $iso): string
{
    $t = strtotime($iso);
    return $t ? date('d/m/Y', $t) : '';
}
