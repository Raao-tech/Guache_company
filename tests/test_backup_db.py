import os
import sqlite3
from datetime import datetime, timedelta

from deploy import backup_db


def _crear_db_de_prueba(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE cotizaciones (id INTEGER PRIMARY KEY, folio TEXT)")
    conn.execute("INSERT INTO cotizaciones (folio) VALUES ('COT-TEST-1')")
    conn.commit()
    conn.close()


def test_hacer_backup_copia_los_datos(tmp_path, monkeypatch):
    db_path = tmp_path / "cotizaciones.db"
    backup_dir = tmp_path / "backups"
    _crear_db_de_prueba(db_path)

    monkeypatch.setattr(backup_db, "DB_PATH", db_path)
    monkeypatch.setattr(backup_db, "BACKUP_DIR", backup_dir)

    destino = backup_db.hacer_backup()

    assert destino.exists()
    filas = sqlite3.connect(destino).execute("SELECT folio FROM cotizaciones").fetchall()
    assert filas == [("COT-TEST-1",)]


def test_limpiar_backups_antiguos_borra_solo_los_viejos(tmp_path, monkeypatch):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    viejo = backup_dir / "cotizaciones_viejo.db"
    nuevo = backup_dir / "cotizaciones_nuevo.db"
    viejo.touch()
    nuevo.touch()

    hace_20_dias = (datetime.now() - timedelta(days=20)).timestamp()
    os.utime(viejo, (hace_20_dias, hace_20_dias))

    monkeypatch.setattr(backup_db, "BACKUP_DIR", backup_dir)
    backup_db.limpiar_backups_antiguos()

    assert not viejo.exists()
    assert nuevo.exists()
