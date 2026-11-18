#!/usr/bin/env bash
# Cliente de terminal de la API. Compila solo si hace falta (no hay clases o algún .java
# es más nuevo) y pasa los argumentos tal cual.
# Ejemplos: ./cliente.sh listar --disponibles    ./cliente.sh prestar 2 Ana --dias 7
set -euo pipefail
cd "$(dirname "$0")"
CLASE=out/biblioteca/cliente/ClienteCli.class
if [ ! -f "$CLASE" ] || [ -n "$(find src -name '*.java' -newer "$CLASE" | head -1)" ]; then
    ./compilar.sh > /dev/null
fi
exec java -cp out biblioteca.cliente.ClienteCli "$@"
