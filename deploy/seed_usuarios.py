#!/usr/bin/env python3
"""
Crea los usuarios iniciales del panel de administración. Idempotente:
si un username ya existe, no lo toca (no pisa la clave ni los permisos).

Uso:
    venv/bin/python deploy/seed_usuarios.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bcrypt

from src.database import Base, SessionLocal, UsuarioDB, engine

TODOS_LOS_PERMISOS = {
    "permiso_productos": True,
    "permiso_blog": True,
    "permiso_asistente": True,
    "permiso_conversaciones": True,
    "permiso_usuarios": True,
    "permiso_pedidos": True,
}
PERMISOS_ASISTENTE = {**TODOS_LOS_PERMISOS, "permiso_usuarios": False}

USUARIOS = [
    {"username": "Developer_1", "clave": "6871_raao", "permisos": TODOS_LOS_PERMISOS},
    {"username": "Senaida", "clave": "SES_acarigua1998", "permisos": TODOS_LOS_PERMISOS},
    {"username": "Assistent_1", "clave": "12345_assistent", "permisos": PERMISOS_ASISTENTE},
]


def main() -> None:
    Base.metadata.create_all(bind=engine)  # no-op si las tablas ya existen (las crea alembic)
    db = SessionLocal()
    try:
        creados = 0
        for u in USUARIOS:
            existe = db.query(UsuarioDB).filter(UsuarioDB.username == u["username"]).first()
            if existe:
                continue
            password_hash = bcrypt.hashpw(u["clave"].encode(), bcrypt.gensalt()).decode()
            db.add(UsuarioDB(username=u["username"], password_hash=password_hash, **u["permisos"]))
            creados += 1
        db.commit()
        print(f"Listo: {creados} usuario(s) nuevo(s) creado(s) (de {len(USUARIOS)} en total).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
