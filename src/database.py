# src/database.py
import os

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
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


# Dependencia de FastAPI compartida por todos los routers — debe ser la
# MISMA función importada en todos lados (no una copia por router), porque
# los tests hacen override por identidad de función
# (app.dependency_overrides[get_db] = ...) y una copia duplicada no
# quedaría interceptada, escribiendo por accidente en la BD real.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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


# Catálogo administrable de venta al detal (sección "Al Detal" de la web).
# Distinto del catálogo mayorista por SKU: acá sí se muestra precio,
# porque son productos/servicios de venta directa al consumidor final,
# no cotizaciones al mayor.
class ProductoDetalDB(Base):
    __tablename__ = "productos_detal"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    descripcion = Column(String, nullable=False)
    precio = Column(Float, nullable=True)
    moneda = Column(String, nullable=True)  # USD, USDT, BTC, EUR, VES, COP, etc. (texto libre)
    imagen_url = Column(String, nullable=True)
    activo = Column(Boolean, default=True, nullable=False)
    orden = Column(Integer, default=0, nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.now)
    fecha_actualizacion = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# Entradas del blog, administrables desde el panel. Reemplaza los
# archivos HTML estáticos que había antes en web/blog/.
class BlogPostDB(Base):
    __tablename__ = "blog_posts"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, index=True, nullable=False)
    titulo = Column(String, nullable=False)
    resumen = Column(String, nullable=False)
    contenido = Column(Text, nullable=False)
    audiencia = Column(String, nullable=True)  # ej. "Para agricultores"
    imagen_url = Column(String, nullable=True)
    publicado = Column(Boolean, default=True, nullable=False)
    fecha_publicacion = Column(DateTime, default=datetime.now)
    fecha_actualizacion = Column(DateTime, default=datetime.now, onupdate=datetime.now)