#!/usr/bin/env bash
# Compila el código y los tests en la carpeta out/
set -euo pipefail
cd "$(dirname "$0")"
rm -rf out
mkdir -p out
javac -encoding UTF-8 -Xlint:all -d out $(find src test -name '*.java')
echo "Compilado en out/"
