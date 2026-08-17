#!/bin/bash
# Script de despliegue, invocado por GitHub Actions vía SSH (ver
# .github/workflows/ci-cd.yml). La llave usada para esto está
# restringida en ~/.ssh/authorized_keys del VPS con un "forced
# command" que SIEMPRE ejecuta este script, sin importar qué
# comando envíe el cliente SSH — así, aunque la clave privada se
# filtrara, no permite ejecutar comandos arbitrarios en el servidor.
set -euo pipefail

cd /var/www/agroguache

git fetch origin
git merge --ff-only origin/main

venv/bin/pip install --quiet -r requirements.txt
venv/bin/alembic upgrade head

systemctl restart agroguache.service
sleep 3

systemctl is-active --quiet agroguache.service
curl -sf http://127.0.0.1:8000/api/health > /dev/null

echo "Deploy OK: $(git rev-parse --short HEAD)"
