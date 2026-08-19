#!/usr/bin/env python3
"""
Crea los usuarios iniciales del panel de administración. Idempotente:
si un username ya existe, no lo toca (no pisa la clave ni el rol).

Uso:
    venv/bin/python deploy/seed_usuarios.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bcrypt

from src.database import Base, SessionLocal, UsuarioDB, engine

USUARIOS = [
    {"username": "Developer_1", "clave": "6871_raao", "rol": "admin"},
    {"username": "Senaida", "clave": "SES_acarigua1998", "rol": "admin"},
    {"username": "Assistent_1", "clave": "12345_assistent", "rol": "asistente"},
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
            db.add(UsuarioDB(username=u["username"], password_hash=password_hash, rol=u["rol"]))
            creados += 1
        db.commit()
        print(f"Listo: {creados} usuario(s) nuevo(s) creado(s) (de {len(USUARIOS)} en total).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
