"""Pruebas mínimas con unittest: python3 -m unittest"""
import argparse
import tempfile
import unittest
from pathlib import Path

import gastos


class TestGastos(unittest.TestCase):
    def setUp(self):
        self.datos = [
            {"id": 1, "fecha": "2026-11-01", "categoria": "comida", "concepto": "a", "importe": 10.0},
            {"id": 3, "fecha": "2026-10-20", "categoria": "ocio", "concepto": "b", "importe": 30.0},
            {"id": 4, "fecha": "2026-11-05", "categoria": "comida", "concepto": "c", "importe": 5.5},
        ]

    def test_importe(self):
        self.assertEqual(gastos.importe_positivo("12,50"), 12.5)
        for malo in ("abc", "0", "-3"):
            with self.assertRaises(argparse.ArgumentTypeError):
                gastos.importe_positivo(malo)

    def test_fechas(self):
        self.assertEqual(gastos.fecha_iso("2026-11-13"), "2026-11-13")
        with self.assertRaises(argparse.ArgumentTypeError):
            gastos.fecha_iso("13/11/2026")
        with self.assertRaises(argparse.ArgumentTypeError):
            gastos.mes_iso("2026-13")

    def test_filtrar_y_totales(self):
        nov = gastos.filtrar(self.datos, "2026-11", None)
        self.assertEqual(len(nov), 2)
        self.assertEqual(len(gastos.filtrar(self.datos, None, "OCIO")), 1)
        self.assertEqual(gastos.totales_por_categoria(self.datos), {"ocio": 30.0, "comida": 15.5})

    def test_siguiente_id(self):
        self.assertEqual(gastos.siguiente_id([]), 1)
        self.assertEqual(gastos.siguiente_id(self.datos), 5)

    def test_ciclo_completo(self):
        with tempfile.TemporaryDirectory() as d:
            f = str(Path(d) / "g.json")
            gastos.main(["--fichero", f, "añadir", "9.99", "Ocio", "Cine"])
            gastos.main(["--fichero", f, "add", "20", "comida", "Súper", "--fecha", "2026-11-02"])
            self.assertEqual(len(gastos.cargar(Path(f))), 2)
            gastos.main(["--fichero", f, "borrar", "1"])
            quedan = gastos.cargar(Path(f))
            self.assertEqual([g["id"] for g in quedan], [2])


if __name__ == "__main__":
    unittest.main()
