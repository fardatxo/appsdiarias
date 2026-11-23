<?php
declare(strict_types=1);

namespace Kanban;

/** Error de datos de entrada: lleva un mensaje por campo para mostrarlo en el formulario. */
final class ErrorValidacion extends \RuntimeException
{
    /** @param array<string,string> $errores campo => mensaje */
    public function __construct(public readonly array $errores)
    {
        parent::__construct(implode(' ', $errores));
    }
}
