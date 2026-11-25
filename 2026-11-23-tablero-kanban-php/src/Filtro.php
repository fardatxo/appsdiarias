<?php
declare(strict_types=1);

namespace Kanban;

/**
 * Filtro de tarjetas a partir de la query string (?q=...&etiqueta=...&estado=...).
 * Se aplica en PHP sobre las tarjetas ya cargadas: un tablero tiene pocas
 * decenas de tarjetas y así la lógica es fácil de leer y de probar.
 */
final class Filtro
{
    /** Valores aceptados en ?estado= => texto visible */
    public const ESTADOS = [
        'vencidas' => 'Vencidas',
        'hoy' => 'Vencen hoy',
        'con_fecha' => 'Con fecha límite',
        'sin_fecha' => 'Sin fecha límite',
    ];

    public const MAX_TEXTO = 100;

    private function __construct(
        public readonly string $texto,
        public readonly string $etiqueta,
        public readonly string $estado,
    ) {
    }

    /** Crea el filtro ignorando valores desconocidos (nunca falla). */
    public static function desdeConsulta(array $consulta): self
    {
        // ?q[]=x llega como array: cualquier cosa que no sea texto se ignora
        $leer = fn (string $clave): string => is_string($consulta[$clave] ?? null) ? $consulta[$clave] : '';
        $texto = mb_substr(trim($leer('q')), 0, self::MAX_TEXTO);
        $etiqueta = $leer('etiqueta');
        $estado = $leer('estado');
        return new self(
            $texto,
            isset(Tarjetas::ETIQUETAS[$etiqueta]) ? $etiqueta : '',
            isset(self::ESTADOS[$estado]) ? $estado : '',
        );
    }

    public function activo(): bool
    {
        return $this->texto !== '' || $this->etiqueta !== '' || $this->estado !== '';
    }

    /** ¿La tarjeta cumple todas las condiciones del filtro? */
    public function coincide(array $tarjeta, ?string $hoy = null): bool
    {
        if ($this->etiqueta !== '' && $tarjeta['etiqueta'] !== $this->etiqueta) {
            return false;
        }
        if ($this->estado !== '') {
            $fecha = (string) $tarjeta['fecha_limite'];
            $ok = match ($this->estado) {
                'vencidas' => estado_fecha($fecha, $hoy) === 'vencida',
                'hoy' => estado_fecha($fecha, $hoy) === 'hoy',
                'con_fecha' => $fecha !== '',
                'sin_fecha' => $fecha === '',
            };
            if (!$ok) {
                return false;
            }
        }
        if ($this->texto !== '') {
            // Busca en título y descripción sin distinguir mayúsculas ni tildes
            $donde = normalizar($tarjeta['titulo'] . ' ' . $tarjeta['descripcion']);
            foreach (preg_split('/\s+/', normalizar($this->texto)) as $palabra) {
                if (!str_contains($donde, $palabra)) {
                    return false; // todas las palabras deben aparecer
                }
            }
        }
        return true;
    }

    /** Devuelve las columnas dejando solo las tarjetas que coinciden. */
    public function aplicar(array $columnas, ?string $hoy = null): array
    {
        if (!$this->activo()) {
            return $columnas;
        }
        foreach ($columnas as &$col) {
            $col['tarjetas'] = array_values(array_filter(
                $col['tarjetas'],
                fn (array $t) => $this->coincide($t, $hoy),
            ));
        }
        return $columnas;
    }

    /** Parámetros para volver a montar la URL (solo los que tienen valor). */
    public function aConsulta(): array
    {
        return array_filter(['q' => $this->texto, 'etiqueta' => $this->etiqueta, 'estado' => $this->estado]);
    }
}
