<?php
declare(strict_types=1);

namespace Kanban;

/**
 * Calcula números de un tablero a partir de sus columnas con tarjetas
 * (el mismo array que pinta la vista). Es una clase "pura": sin BD,
 * recibe datos y devuelve datos, así se prueba en una línea.
 */
final class Estadisticas
{
    public static function calcular(array $columnas, ?string $hoy = null): array
    {
        $hoy ??= date('Y-m-d');
        $total = 0;
        $porColumna = [];
        $porEtiqueta = array_fill_keys(array_keys(Tarjetas::ETIQUETAS), 0);
        $porEtiqueta[''] = 0; // sin etiqueta
        $vencidas = $venceHoy = $conFecha = 0;
        $proximas = []; // tarjetas con fecha que aún no han vencido

        foreach ($columnas as $i => $col) {
            $n = count($col['tarjetas']);
            $total += $n;
            $porColumna[] = ['nombre' => $col['nombre'], 'tarjetas' => $n];
            // La última columna se considera "terminado": no cuentan sus vencidas
            $esUltima = $i === array_key_last($columnas);
            foreach ($col['tarjetas'] as $t) {
                $etiqueta = isset($porEtiqueta[$t['etiqueta']]) ? $t['etiqueta'] : '';
                $porEtiqueta[$etiqueta]++;
                if ($t['fecha_limite'] === '') {
                    continue;
                }
                $conFecha++;
                if ($esUltima) {
                    continue;
                }
                match (estado_fecha($t['fecha_limite'], $hoy)) {
                    'vencida' => $vencidas++,
                    'hoy' => $venceHoy++,
                    default => $proximas[] = ['titulo' => $t['titulo'], 'fecha_limite' => $t['fecha_limite'], 'columna' => $col['nombre']],
                };
            }
        }

        usort($proximas, fn ($a, $b) => strcmp($a['fecha_limite'], $b['fecha_limite']));
        $hechas = $columnas ? count($columnas[array_key_last($columnas)]['tarjetas']) : 0;

        return [
            'total' => $total,
            'hechas' => $hechas,
            // Progreso = % de tarjetas en la última columna
            'progreso' => $total > 0 ? (int) round($hechas * 100 / $total) : 0,
            'por_columna' => $porColumna,
            'por_etiqueta' => $porEtiqueta,
            'con_fecha' => $conFecha,
            'vencidas' => $vencidas,
            'vencen_hoy' => $venceHoy,
            'proximas' => array_slice($proximas, 0, 5),
        ];
    }
}
