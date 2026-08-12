# src/database.py
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# Archivo local de SQLite donde se guardarán los datos
SQLALCHEMY_DATABASE_URL = "sqlite:///./cotizaciones.db"

# Motor de la base de datos (check_same_thread=False es necesario en FastAPI con SQLite)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

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