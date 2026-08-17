import uuid
import secrets
import logging
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# Importaciones internas
from src import config
from src.services.llm_service import generar_respuesta_llm
from src.bots.telegram_bot import crear_aplicacion_bot
from src.database import engine, Base, SessionLocal, CotizacionDB

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("agroguache_api")

# Preparamos el bot de Telegram
telegram_app = crear_aplicacion_bot()

# Definimos el ciclo de vida (Lifespan) del servidor
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- PROCESOS AL INICIAR EL SERVIDOR ---
    # 1. Crear las tablas de la base de datos si no existen
    logger.info("🗄️ Inicializando base de datos SQLite...")
    Base.metadata.create_all(bind=engine)

    # 2. Iniciar Bot de Telegram
    if telegram_app:
        logger.info("🦊 Iniciando el Zorro Guache en Telegram (segundo plano)...")
        await telegram_app.initialize()
        await telegram_app.start()
        await telegram_app.updater.start_polling()
    
    yield  # FastAPI escuchando tráfico web
    
    # --- PROCESOS AL APAGAR EL SERVIDOR ---
    if telegram_app:
        logger.info("🛑 Deteniendo el bot de Telegram limpiamente...")
        await telegram_app.updater.stop()
        await telegram_app.stop()
        await telegram_app.shutdown()

app = FastAPI(
    title="Agroindustria Guache API",
    description="Backend unificado: Web + Asistente Virtual + Base de Datos",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# DEPENDENCIA DE BASE DE DATOS
# ------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------------------------------------------------------
# DEPENDENCIA DE AUTENTICACIÓN (ADMINISTRACIÓN)
# ------------------------------------------------------------------
security = HTTPBasic()

def verificar_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Protege endpoints administrativos con HTTP Basic Auth mientras el proyecto
    no cuenta con un sistema de usuarios/roles (ver §7-8.2 del documento técnico).
    """
    usuario_ok = secrets.compare_digest(credentials.username, config.ADMIN_USERNAME)
    clave_ok = secrets.compare_digest(credentials.password, config.ADMIN_PASSWORD)
    if not (usuario_ok and clave_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de administrador inválidas.",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# ------------------------------------------------------------------
# MODELOS PYDANTIC
# ------------------------------------------------------------------
class CotizacionRequest(BaseModel):
    nombre_contacto: str = Field(..., min_length=2)
    telefono: str = Field(..., min_length=7)
    empresa: Optional[str] = None
    sku_producto: str
    cantidad_toneladas: float = Field(..., gt=0)
    destino_despacho: str = Field(..., min_length=3)
    observaciones: Optional[str] = None

class CotizacionResponse(BaseModel):
    exito: bool
    id_cotizacion: str
    mensaje: str

class ChatRequest(BaseModel):
    mensaje: str = Field(..., min_length=1)

class ChatResponse(BaseModel):
    respuesta: str

class CotizacionDetalle(BaseModel):
    id: int
    folio: str
    nombre_contacto: str
    telefono: str
    empresa: Optional[str]
    sku_producto: str
    cantidad_toneladas: float
    destino_despacho: str
    observaciones: Optional[str]
    fecha_registro: datetime

    model_config = {"from_attributes": True}
# ------------------------------------------------------------------
# ENDPOINTS DE LA API
# ------------------------------------------------------------------
@app.get("/api/health", tags=["Salud"])
async def health_check():
    return {"status": "ok", "servicio": "Agroindustria Guache C.A."}

@app.post("/api/cotizar", response_model=CotizacionResponse, tags=["Cotizaciones"])
async def registrar_cotizacion(payload: CotizacionRequest, db: Session = Depends(get_db)):
    """
    Recibe la cotización de la web y la guarda de forma persistente en SQLite.
    """
    try:
        folio = f"COT-{datetime.now().year}-{uuid.uuid4().hex[:8].upper()}"
        
        # 1. Crear el objeto de base de datos
        nueva_cotizacion = CotizacionDB(
            folio=folio,
            nombre_contacto=payload.nombre_contacto,
            telefono=payload.telefono,
            empresa=payload.empresa,
            sku_producto=payload.sku_producto,
            cantidad_toneladas=payload.cantidad_toneladas,
            destino_despacho=payload.destino_despacho,
            observaciones=payload.observaciones
        )
        
        # 2. Guardar en SQLite
        db.add(nueva_cotizacion)
        db.commit()
        db.refresh(nueva_cotizacion)

        logger.info(f"✅ Cotización GUARDADA en BD [{folio}] - Cliente: {payload.nombre_contacto}")

        return CotizacionResponse(
            exito=True,
            id_cotizacion=folio,
            mensaje="Hemos recibido tu solicitud. Nuestro departamento comercial te contactará a la brevedad."
        )
    except Exception as e:
        logger.error(f"❌ Error al guardar cotización en BD: {e}")
        db.rollback() # Revertir si hay error
        raise HTTPException(status_code=500, detail="Error interno al registrar la cotización.")

@app.get("/api/cotizaciones", response_model=list[CotizacionDetalle], tags=["Administración"])
async def listar_cotizaciones(db: Session = Depends(get_db), _admin: str = Depends(verificar_admin)):
    """
    Devuelve el historial completo de cotizaciones registradas,
    ordenadas desde la más reciente a la más antigua.
    Protegido con HTTP Basic Auth (ADMIN_USERNAME / ADMIN_PASSWORD).
    """
    try:
        # Consultamos todas las cotizaciones ordenadas por fecha descendente
        cotizaciones = db.query(CotizacionDB).order_by(CotizacionDB.fecha_registro.desc()).all()
        return cotizaciones
    except Exception as e:
        logger.error(f"Error al obtener las cotizaciones: {e}")
        raise HTTPException(status_code=500, detail="Error interno al consultar la base de datos.")
    
@app.post("/api/chat", response_model=ChatResponse, tags=["Asistente Guache"])
async def chat_guache(payload: ChatRequest):
    try:
        respuesta_bot = await generar_respuesta_llm(prompt_usuario=payload.mensaje)
        return ChatResponse(respuesta=respuesta_bot)
    except Exception as e:
        logger.error(f"Error en chat Guache: {e}")
        raise HTTPException(status_code=500, detail="Error al procesar la respuesta.")

# ------------------------------------------------------------------
# ARCHIVOS ESTÁTICOS
# ------------------------------------------------------------------
app.mount("/", StaticFiles(directory="web", html=True), name="web")