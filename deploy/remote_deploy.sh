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
venv/bin/python deploy/seed_blog.py      # idempotente: no duplica si ya corrió antes
venv/bin/python deploy/seed_usuarios.py  # idempotente: no duplica si ya corrió antes

# Verificación: un deploy pasado corrió los seeds sin error pero no
# insertó nada (causa no determinada) y el pipeline igual reportó éxito.
# Esto convierte ese escenario en un fallo visible del deploy, en vez
# de un silencio que hay que descubrir probando a mano después.
venv/bin/python -c "
from src.database import SessionLocal, BlogPostDB, UsuarioDB
db = SessionLocal()
try:
    posts = db.query(BlogPostDB).count()
    usuarios = db.query(UsuarioDB).count()
finally:
    db.close()
assert posts >= 4, f'Se esperaban al menos 4 posts de blog, hay {posts}'
assert usuarios >= 3, f'Se esperaban al menos 3 usuarios, hay {usuarios}'
print(f'Verificación de seeds OK: {posts} posts, {usuarios} usuarios')
"

systemctl restart agroguache.service
sleep 3

systemctl is-active --quiet agroguache.service
curl -sf http://127.0.0.1:8000/api/health > /dev/null

echo "Deploy OK: $(git rev-parse --short HEAD)"
