#!/usr/bin/env bash
# Compila y ejecuta todos los tests
set -euo pipefail
cd "$(dirname "$0")"
./compilar.sh
java -cp out biblioteca.Pruebas
