# src/database.py
import os

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# Postgres en producción (DATABASE_URL en .env), SQLite por defecto en desarrollo local
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cotizaciones.db")

# check_same_thread=False solo aplica (y solo lo acepta) el driver de SQLite
connect_args = (
    {"check_same_thread": False}
    if SQLALCHEMY_DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)

# Creador de sesiones para interactuar con la BD
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Clase base para definir los modelos
Base = declarative_base()

# Modelo (Tabla) de Cotizaciones
class CotizacionDB(Base):
    __tablename__ = "cotizaciones"

    id = Column(Integer, primary_key=True, index=True)
    folio = Column(String, unique=True, index=True)
    nombre_contacto = Column(String, index=True)
    telefono = Column(String)
    empresa = Column(String, nullable=True)
    sku_producto = Column(String, index=True)
    cantidad_toneladas = Column(Float)
    destino_despacho = Column(String)
    observaciones = Column(String, nullable=True)
    fecha_registro = Column(DateTime, default=datetime.now)