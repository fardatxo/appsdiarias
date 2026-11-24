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

/** ¿Es "AAAA-MM-DD" y una fecha real? (rechaza 2026-02-30) */
function fecha_valida(string $fecha): bool
{
    $d = DateTimeImmutable::createFromFormat('!Y-m-d', $fecha);
    return $d !== false && $d->format('Y-m-d') === $fecha;
}

/**
 * Estado de una fecha límite respecto a hoy: 'vencida', 'hoy' o ''.
 * Las fechas ISO se pueden comparar como texto.
 */
function estado_fecha(string $fecha, ?string $hoy = null): string
{
    if ($fecha === '') {
        return '';
    }
    $hoy ??= date('Y-m-d');
    return match (true) {
        $fecha < $hoy => 'vencida',
        $fecha === $hoy => 'hoy',
        default => '',
    };
}
