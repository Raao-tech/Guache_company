#!/usr/bin/env python3
"""
Migración única de datos: copia todas las filas de cotizaciones.db
(SQLite) a la base Postgres apuntada por DATABASE_URL.

Uso (en el VPS, DESPUÉS de correr `alembic upgrade head` contra la
Postgres nueva, para que la tabla ya exista con el esquema correcto):

    DATABASE_URL="postgresql+psycopg://usuario:clave@localhost/agroguache" \
        venv/bin/python deploy/migrate_sqlite_to_postgres.py

No modifica cotizaciones.db. Si la tabla en Postgres ya tiene filas,
aborta sin insertar nada para no duplicar datos.
"""
import os
import sqlite3
import sys
from pathlib import Path

import sqlalchemy as sa

SQLITE_PATH = Path("cotizaciones.db")

COLUMNAS = (
    "id", "folio", "nombre_contacto", "telefono", "empresa", "sku_producto",
    "cantidad_toneladas", "destino_despacho", "observaciones", "fecha_registro",
)


def main() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url or database_url.startswith("sqlite"):
        sys.exit("DATABASE_URL debe apuntar a Postgres (revisá el .env de producción).")

    if not SQLITE_PATH.exists():
        sys.exit(f"No se encontró {SQLITE_PATH.resolve()}")

    engine = sa.create_engine(database_url)

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    filas = sqlite_conn.execute(
        f"SELECT {', '.join(COLUMNAS)} FROM cotizaciones ORDER BY id"
    ).fetchall()
    sqlite_conn.close()

    with engine.begin() as conn:
        ya_existen = conn.execute(sa.text("SELECT COUNT(*) FROM cotizaciones")).scalar()
        if ya_existen:
            sys.exit(
                f"La tabla 'cotizaciones' en Postgres ya tiene {ya_existen} fila(s) — "
                "abortando para no duplicar datos."
            )

        insert = sa.text(
            "INSERT INTO cotizaciones (" + ", ".join(COLUMNAS) + ") "
            "VALUES (" + ", ".join(f":{c}" for c in COLUMNAS) + ")"
        )
        for fila in filas:
            conn.execute(insert, dict(fila))

        # Sincronizar la secuencia del id autoincremental con el máximo id migrado
        conn.execute(
            sa.text(
                "SELECT setval(pg_get_serial_sequence('cotizaciones', 'id'), "
                "COALESCE((SELECT MAX(id) FROM cotizaciones), 1))"
            )
        )

    print(f"Migradas {len(filas)} fila(s) de {SQLITE_PATH} a Postgres.")


if __name__ == "__main__":
    main()
