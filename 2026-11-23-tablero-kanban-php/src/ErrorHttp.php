<?php
declare(strict_types=1);

namespace Kanban;

/** Error que se traduce directamente en un código HTTP (404, 405, 419...). */
final class ErrorHttp extends \RuntimeException
{
    public function __construct(public readonly int $estado, string $mensaje)
    {
        parent::__construct($mensaje);
    }
}
