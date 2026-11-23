<?php
declare(strict_types=1);

namespace Kanban;

/**
 * Protección CSRF: cada sesión tiene un token aleatorio que todos
 * los formularios POST deben devolver en el campo oculto "_token".
 */
final class Csrf
{
    public static function token(): string
    {
        if (empty($_SESSION['_token'])) {
            $_SESSION['_token'] = bin2hex(random_bytes(16));
        }
        return $_SESSION['_token'];
    }

    /** Campo oculto listo para pegar dentro de un <form>. */
    public static function campo(): string
    {
        return '<input type="hidden" name="_token" value="' . self::token() . '">';
    }

    /** Lanza 419 si el token no coincide (comparación en tiempo constante). */
    public static function comprobar(?string $enviado): void
    {
        if (!is_string($enviado) || !hash_equals(self::token(), $enviado)) {
            throw new ErrorHttp(419, 'La sesión ha caducado. Recarga la página e inténtalo de nuevo.');
        }
    }
}
