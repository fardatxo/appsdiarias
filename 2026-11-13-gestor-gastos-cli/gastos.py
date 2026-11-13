#!/usr/bin/env python3
"""Gestor de gastos personales por línea de comandos.

Guarda los gastos en un fichero JSON y permite añadir, listar,
borrar y ver un resumen por categoría con un gráfico de barras en texto.
Solo usa la biblioteca estándar de Python.
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

# Fichero de datos por defecto: junto al script
FICHERO_POR_DEFECTO = Path(__file__).with_name("gastos.json")


# ---------- Persistencia ----------

def cargar(ruta: Path) -> list[dict]:
    """Lee la lista de gastos del JSON (lista vacía si aún no existe)."""
    if not ruta.exists():
        return []
    try:
        with ruta.open(encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        sys.exit(f"Error: {ruta} no contiene JSON válido.")


def guardar(ruta: Path, gastos: list[dict]) -> None:
    """Escribe la lista de gastos en el JSON, con sangría para que sea legible."""
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(gastos, f, ensure_ascii=False, indent=2)


# ---------- Validadores para argparse ----------

def importe_positivo(texto: str) -> float:
    """Convierte '12,50' o '12.50' en float y exige que sea mayor que cero."""
    try:
        valor = float(texto.replace(",", "."))
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{texto}' no es un número")
    if valor <= 0:
        raise argparse.ArgumentTypeError("el importe debe ser mayor que 0")
    return round(valor, 2)


def fecha_iso(texto: str) -> str:
    """Comprueba que la fecha tenga formato AAAA-MM-DD."""
    try:
        return date.fromisoformat(texto).isoformat()
    except ValueError:
        raise argparse.ArgumentTypeError("la fecha debe tener formato AAAA-MM-DD")


def mes_iso(texto: str) -> str:
    """Comprueba que el mes tenga formato AAAA-MM."""
    try:
        date.fromisoformat(texto + "-01")
    except ValueError:
        raise argparse.ArgumentTypeError("el mes debe tener formato AAAA-MM")
    return texto


# ---------- Lógica ----------

def filtrar(gastos: list[dict], mes: str | None, categoria: str | None) -> list[dict]:
    """Devuelve los gastos que coinciden con el mes y/o la categoría."""
    resultado = gastos
    if mes:
        resultado = [g for g in resultado if g["fecha"].startswith(mes)]
    if categoria:
        resultado = [g for g in resultado if g["categoria"] == categoria.lower()]
    return resultado


def siguiente_id(gastos: list[dict]) -> int:
    """El id nuevo es el mayor existente + 1 (así no se reutilizan ids)."""
    return max((g["id"] for g in gastos), default=0) + 1


def totales_por_categoria(gastos: list[dict]) -> dict[str, float]:
    """Suma los importes agrupando por categoría, de mayor a menor."""
    totales: dict[str, float] = defaultdict(float)
    for g in gastos:
        totales[g["categoria"]] += g["importe"]
    return dict(sorted(totales.items(), key=lambda par: par[1], reverse=True))


# ---------- Comandos ----------

def cmd_añadir(args, gastos):
    gasto = {
        "id": siguiente_id(gastos),
        "fecha": args.fecha,
        "categoria": args.categoria.lower(),
        "concepto": args.concepto,
        "importe": args.importe,
    }
    gastos.append(gasto)
    guardar(args.fichero, gastos)
    print(f"Añadido #{gasto['id']}: {gasto['concepto']} ({gasto['importe']:.2f} €)")


def cmd_listar(args, gastos):
    seleccion = sorted(filtrar(gastos, args.mes, args.categoria), key=lambda g: g["fecha"])
    if not seleccion:
        print("No hay gastos que mostrar.")
        return
    print(f"{'ID':>3}  {'Fecha':<10}  {'Categoría':<12}  {'Importe':>9}  Concepto")
    print("-" * 56)
    for g in seleccion:
        print(f"{g['id']:>3}  {g['fecha']:<10}  {g['categoria']:<12}  "
              f"{g['importe']:>7.2f} €  {g['concepto']}")
    print("-" * 56)
    print(f"Total: {sum(g['importe'] for g in seleccion):.2f} € en {len(seleccion)} gasto(s)")


def cmd_borrar(args, gastos):
    restantes = [g for g in gastos if g["id"] != args.id]
    if len(restantes) == len(gastos):
        sys.exit(f"Error: no existe ningún gasto con id {args.id}.")
    guardar(args.fichero, restantes)
    print(f"Gasto #{args.id} borrado.")


def cmd_resumen(args, gastos):
    seleccion = filtrar(gastos, args.mes, None)
    if not seleccion:
        print("No hay gastos que resumir.")
        return
    totales = totales_por_categoria(seleccion)
    total = sum(totales.values())
    maximo = max(totales.values())
    ANCHO = 30  # longitud de la barra más larga
    print(f"Resumen {args.mes or 'de todos los gastos'}")
    for categoria, importe in totales.items():
        barra = "█" * max(1, round(importe / maximo * ANCHO))
        print(f"{categoria:<12} {barra:<{ANCHO}} {importe:>8.2f} €  {importe / total:>4.0%}")
    print(f"{'TOTAL':<12} {'':<{ANCHO}} {total:>8.2f} €")
    print(f"Gasto medio: {total / len(seleccion):.2f} €")


# ---------- Interfaz de línea de comandos ----------

def crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gestor de gastos personales en JSON.")
    parser.add_argument("--fichero", type=Path, default=FICHERO_POR_DEFECTO,
                        help="ruta del JSON de datos (por defecto: gastos.json)")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("añadir", aliases=["add"], help="añade un gasto")
    p.add_argument("importe", type=importe_positivo)
    p.add_argument("categoria")
    p.add_argument("concepto")
    p.add_argument("--fecha", type=fecha_iso, default=date.today().isoformat(),
                   help="AAAA-MM-DD (por defecto, hoy)")
    p.set_defaults(func=cmd_añadir)

    p = sub.add_parser("listar", aliases=["ls"], help="lista los gastos")
    p.add_argument("--mes", type=mes_iso, help="filtra por mes AAAA-MM")
    p.add_argument("--categoria", help="filtra por categoría")
    p.set_defaults(func=cmd_listar)

    p = sub.add_parser("borrar", aliases=["rm"], help="borra un gasto por id")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_borrar)

    p = sub.add_parser("resumen", help="totales por categoría con gráfico de barras")
    p.add_argument("--mes", type=mes_iso, help="resume solo el mes AAAA-MM")
    p.set_defaults(func=cmd_resumen)
    return parser


def main(argv=None):
    args = crear_parser().parse_args(argv)
    gastos = cargar(args.fichero)
    args.func(args, gastos)


if __name__ == "__main__":
    main()
