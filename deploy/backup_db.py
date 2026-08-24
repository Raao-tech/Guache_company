#!/usr/bin/env python3
"""
Backup de la base de datos, con rotación de respaldos antiguos. Detecta
el motor via DATABASE_URL (src/database.py) y usa el método correcto:

- SQLite (desarrollo local, o si no se definió DATABASE_URL): backup API
  online de sqlite3 (no una copia cruda del archivo mientras la app
  puede estar escribiendo).
- Postgres (producción): pg_dump en formato comprimido (-F c), restaurable
  con pg_restore.

Pensado para correr vía el timer de systemd (agroguache-backup.timer),
con WorkingDirectory=/var/www/agroguache.
"""
import subprocess
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.database import SQLALCHEMY_DATABASE_URL

DB_PATH = Path("cotizaciones.db")
BACKUP_DIR = Path("/var/backups/agroguache")
RETENCION_DIAS = 14


def hacer_backup_sqlite() -> Path:
    destino = BACKUP_DIR / f"cotizaciones_{datetime.now():%Y-%m-%d_%H%M%S}.db"

    origen = sqlite3.connect(DB_PATH)
    con_destino = sqlite3.connect(destino)
    with con_destino:
        origen.backup(con_destino)
    origen.close()
    con_destino.close()

    return destino


def hacer_backup_postgres() -> Path:
    # pg_dump espera una URI postgresql://, no el dialecto +psycopg de SQLAlchemy
    uri_pg_dump = SQLALCHEMY_DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")
    destino = BACKUP_DIR / f"agroguache_{datetime.now():%Y-%m-%d_%H%M%S}.dump"

    subprocess.run(["pg_dump", uri_pg_dump, "-F", "c", "-f", str(destino)], check=True)

    return destino


def limpiar_backups_antiguos() -> None:
    limite = datetime.now() - timedelta(days=RETENCION_DIAS)
    for patron in ("cotizaciones_*.db", "agroguache_*.dump"):
        for archivo in BACKUP_DIR.glob(patron):
            if datetime.fromtimestamp(archivo.stat().st_mtime) < limite:
                archivo.unlink()


def main() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    if SQLALCHEMY_DATABASE_URL.startswith("postgresql"):
        destino = hacer_backup_postgres()
    else:
        destino = hacer_backup_sqlite()

    limpiar_backups_antiguos()
    print(f"Backup creado: {destino}")


if __name__ == "__main__":
    main()
