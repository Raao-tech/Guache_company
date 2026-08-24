import os
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import patch

from deploy import backup_db


def _crear_db_de_prueba(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE cotizaciones (id INTEGER PRIMARY KEY, folio TEXT)")
    conn.execute("INSERT INTO cotizaciones (folio) VALUES ('COT-TEST-1')")
    conn.commit()
    conn.close()


def test_hacer_backup_sqlite_copia_los_datos(tmp_path, monkeypatch):
    db_path = tmp_path / "cotizaciones.db"
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    _crear_db_de_prueba(db_path)

    monkeypatch.setattr(backup_db, "DB_PATH", db_path)
    monkeypatch.setattr(backup_db, "BACKUP_DIR", backup_dir)

    destino = backup_db.hacer_backup_sqlite()

    assert destino.exists()
    filas = sqlite3.connect(destino).execute("SELECT folio FROM cotizaciones").fetchall()
    assert filas == [("COT-TEST-1",)]


def test_hacer_backup_postgres_llama_pg_dump_con_uri_correcta(tmp_path, monkeypatch):
    backup_dir = tmp_path / "backups"
    monkeypatch.setattr(backup_db, "BACKUP_DIR", backup_dir)
    monkeypatch.setattr(
        backup_db,
        "SQLALCHEMY_DATABASE_URL",
        "postgresql+psycopg://user:pass@localhost:5432/agroguache",
    )

    with patch("deploy.backup_db.subprocess.run") as mock_run:
        destino = backup_db.hacer_backup_postgres()

    comando = mock_run.call_args[0][0]
    assert comando[0] == "pg_dump"
    # pg_dump no entiende el dialecto +psycopg de SQLAlchemy
    assert comando[1] == "postgresql://user:pass@localhost:5432/agroguache"
    assert destino.parent == backup_dir
    assert destino.name.startswith("agroguache_")


def test_main_elige_sqlite_o_postgres_segun_database_url(monkeypatch, tmp_path):
    monkeypatch.setattr(backup_db, "BACKUP_DIR", tmp_path)

    with patch("deploy.backup_db.hacer_backup_sqlite") as mock_sqlite, patch(
        "deploy.backup_db.hacer_backup_postgres"
    ) as mock_postgres, patch("deploy.backup_db.limpiar_backups_antiguos"):
        mock_sqlite.return_value = tmp_path / "x.db"
        monkeypatch.setattr(backup_db, "SQLALCHEMY_DATABASE_URL", "sqlite:///./cotizaciones.db")
        backup_db.main()
        mock_sqlite.assert_called_once()
        mock_postgres.assert_not_called()

    with patch("deploy.backup_db.hacer_backup_sqlite") as mock_sqlite, patch(
        "deploy.backup_db.hacer_backup_postgres"
    ) as mock_postgres, patch("deploy.backup_db.limpiar_backups_antiguos"):
        mock_postgres.return_value = tmp_path / "x.dump"
        monkeypatch.setattr(
            backup_db, "SQLALCHEMY_DATABASE_URL", "postgresql+psycopg://u:p@h/db"
        )
        backup_db.main()
        mock_postgres.assert_called_once()
        mock_sqlite.assert_not_called()


def test_limpiar_backups_antiguos_borra_solo_los_viejos(tmp_path, monkeypatch):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    viejo = backup_dir / "cotizaciones_viejo.db"
    nuevo = backup_dir / "cotizaciones_nuevo.db"
    viejo_pg = backup_dir / "agroguache_viejo.dump"
    viejo.touch()
    nuevo.touch()
    viejo_pg.touch()

    hace_20_dias = (datetime.now() - timedelta(days=20)).timestamp()
    os.utime(viejo, (hace_20_dias, hace_20_dias))
    os.utime(viejo_pg, (hace_20_dias, hace_20_dias))

    monkeypatch.setattr(backup_db, "BACKUP_DIR", backup_dir)
    backup_db.limpiar_backups_antiguos()

    assert not viejo.exists()
    assert not viejo_pg.exists()
    assert nuevo.exists()
