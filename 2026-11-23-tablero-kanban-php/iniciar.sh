#!/usr/bin/env bash
# Arranca la app con el servidor integrado de PHP: http://localhost:8000
cd "$(dirname "$0")"
PUERTO="${1:-8000}"
echo "Kanban PHP en http://localhost:$PUERTO  (Ctrl+C para parar)"
php -S "localhost:$PUERTO" -t public public/index.php
