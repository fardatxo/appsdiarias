#!/usr/bin/env bash
# Compila y arranca la API. Los argumentos se pasan tal cual (p. ej. --puerto 9000)
set -euo pipefail
cd "$(dirname "$0")"
./compilar.sh
exec java -cp out biblioteca.Main "$@"
