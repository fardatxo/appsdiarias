# Gestor de gastos CLI

Pequeño gestor de gastos personales para la terminal. Guarda los gastos en un fichero JSON y permite añadirlos, listarlos (filtrando por mes o categoría), borrarlos y ver un resumen por categoría con un gráfico de barras en texto.

## Tecnologías

- Python 3.10+ (solo biblioteca estándar: `argparse`, `json`, `pathlib`, `collections`, `datetime`)
- `unittest` para las pruebas

## Cómo ejecutarla

```bash
python3 gastos.py añadir 45,30 comida "Compra semanal"
python3 gastos.py añadir 12 ocio "Cine" --fecha 2026-11-07
python3 gastos.py listar --mes 2026-11
python3 gastos.py listar --categoria comida
python3 gastos.py resumen
python3 gastos.py borrar 2
```

Los comandos tienen alias sin «ñ»: `add`, `ls` y `rm`. Los datos se guardan en `gastos.json` junto al script; con `--fichero otra/ruta.json` (antes del comando) se usa otro fichero.

Ejemplo de resumen:

```
Resumen de todos los gastos
comida       ██████████████████████████████    53.80 €   56%
transporte   █████████████████                 30.00 €   31%
ocio         ███████                           12.00 €   13%
TOTAL                                          95.80 €
Gasto medio: 23.95 €
```

Pruebas:

```bash
python3 -m unittest
```

## Qué se aprende

- **Subcomandos con `argparse`**: `add_subparsers`, alias, y validadores propios con `type=` que lanzan `ArgumentTypeError`.
- **Persistencia en JSON**: leer y escribir una lista de diccionarios con `json` y `pathlib`.
- **Agrupar y ordenar datos**: `defaultdict`, comprensiones de listas y `sorted` con `key`.
- **Formato de texto con f-strings**: alineación, decimales y porcentajes para pintar tablas y barras.
