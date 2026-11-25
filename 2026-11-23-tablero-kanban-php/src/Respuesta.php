<?php
declare(strict_types=1);

namespace Kanban;

/** Respuesta HTTP como objeto: se construye en App y se envía en index.php. */
final class Respuesta
{
    /** @param array<string,string> $cabeceras */
    public function __construct(
        public readonly int $estado,
        public readonly array $cabeceras,
        public readonly string $cuerpo,
    ) {
    }

    public static function html(string $html, int $estado = 200): self
    {
        return new self($estado, ['Content-Type' => 'text/html; charset=utf-8'], $html);
    }

    /** Respuesta JSON (la usa el arrastrar y soltar). */
    public static function json(array $datos, int $estado = 200): self
    {
        return new self(
            $estado,
            ['Content-Type' => 'application/json; charset=utf-8'],
            json_encode($datos, JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR),
        );
    }

    /** Fichero para descargar (exportar a JSON o CSV). */
    public static function descarga(string $contenido, string $tipo, string $nombreFichero): self
    {
        return new self(200, [
            'Content-Type' => $tipo,
            'Content-Disposition' => 'attachment; filename="' . $nombreFichero . '"',
        ], $contenido);
    }

    /** 303 See Other: tras un POST el navegador vuelve con GET (patrón PRG). */
    public static function redirigir(string $url): self
    {
        return new self(303, ['Location' => $url], '');
    }

    public function enviar(): void
    {
        http_response_code($this->estado);
        foreach ($this->cabeceras as $nombre => $valor) {
            header("$nombre: $valor");
        }
        echo $this->cuerpo;
    }
}
