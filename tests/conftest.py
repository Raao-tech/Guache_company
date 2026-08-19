import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fastapi.testclient import TestClient

import main
from src import config
from src.database import Base, get_db


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """
    TestClient con el bot de Telegram deshabilitado (evita llamadas de red)
    y una base de datos SQLite temporal y aislada por test.
    """
    monkeypatch.setattr(main, "telegram_app", None)

    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = override_get_db
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()


@pytest.fixture()
def admin_auth():
    return (config.ADMIN_USERNAME, config.ADMIN_PASSWORD)


@pytest.fixture()
def cotizacion_payload():
    return {
        "nombre_contacto": "Juan Pérez",
        "telefono": "04141234567",
        "empresa": "Distribuidora El Llano",
        "sku_producto": "HM-050",
        "cantidad_toneladas": 12.5,
        "destino_despacho": "Barinas",
        "observaciones": "Entrega en la mañana",
    }
