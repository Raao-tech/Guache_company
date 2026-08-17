#!/usr/bin/env python3
"""
Backup seguro de cotizaciones.db (usa el API de respaldo online de
sqlite3, no una copia cruda del archivo) con rotación de respaldos
antiguos.

Pensado para correr vía el timer de systemd (agroguache-backup.timer),
con WorkingDirectory=/var/www/agroguache — usa la misma ruta relativa
que la app real (src/database.py) para no duplicar configuración.
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path("cotizaciones.db")
BACKUP_DIR = Path("/var/backups/agroguache")
RETENCION_DIAS = 14


def hacer_backup() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    destino = BACKUP_DIR / f"cotizaciones_{timestamp}.db"

    origen = sqlite3.connect(DB_PATH)
    con_destino = sqlite3.connect(destino)
    with con_destino:
        origen.backup(con_destino)
    origen.close()
    con_destino.close()

    return destino


def limpiar_backups_antiguos() -> None:
    limite = datetime.now() - timedelta(days=RETENCION_DIAS)
    for archivo in BACKUP_DIR.glob("cotizaciones_*.db"):
        if datetime.fromtimestamp(archivo.stat().st_mtime) < limite:
            archivo.unlink()


if __name__ == "__main__":
    destino = hacer_backup()
    limpiar_backups_antiguos()
    print(f"Backup creado: {destino}")
