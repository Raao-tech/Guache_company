import uuid
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Importamos la función exacta definida en src/services/llm_service.py
from src.services.llm_service import generar_respuesta_llm

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("agroguache_api")

app = FastAPI(
    title="Agroindustria Guache API",
    description="Backend para cotizaciones e integración con LLM via Groq",
    version="1.0.0"
)

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# MODELOS PYDANTIC (Coinciden con el payload de web/app.js)
# ------------------------------------------------------------------

class CotizacionRequest(BaseModel):
    nombre_contacto: str = Field(..., min_length=2, description="Nombre y apellido")
    telefono: str = Field(..., min_length=7, description="Teléfono / WhatsApp")
    empresa: Optional[str] = Field(None, description="Empresa o Razón social")
    sku_producto: str = Field(..., description="SKU del producto solicitado")
    cantidad_toneladas: float = Field(..., gt=0, description="Cantidad en toneladas")
    destino_despacho: str = Field(..., min_length=3, description="Lugar de entrega")
    observaciones: Optional[str] = Field(None, description="Observaciones adicionales")

class CotizacionResponse(BaseModel):
    exito: bool
    id_cotizacion: str
    mensaje: str

class ChatRequest(BaseModel):
    mensaje: str = Field(..., min_length=1, description="Mensaje del usuario")

class ChatResponse(BaseModel):
    respuesta: str


# ------------------------------------------------------------------
# ENDPOINTS DE LA API (/api/*)
# ------------------------------------------------------------------

@app.get("/api/health", tags=["Salud"])
async def health_check():
    """Verificación de estado de la API."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "servicio": "Agroindustria Guache C.A."
    }


@app.post("/api/cotizar", response_model=CotizacionResponse, tags=["Cotizaciones"])
async def registrar_cotizacion(payload: CotizacionRequest):
    """
    Registra una solicitud de cotización y genera un folio único.
    """
    try:
        folio = f"COT-{datetime.now().year}-{uuid.uuid4().hex[:8].upper()}"
        logger.info(f"Cotización registrada [{folio}] - Cliente: {payload.nombre_contacto}")

        return CotizacionResponse(
            exito=True,
            id_cotizacion=folio,
            mensaje="Hemos recibido tu solicitud. Nuestro departamento comercial te contactará a la brevedad."
        )

    except Exception as e:
        logger.error(f"Error al registrar cotización: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al registrar la cotización."
        )


@app.post("/api/chat", response_model=ChatResponse, tags=["Asistente Guache"])
async def chat_guache(payload: ChatRequest):
    """
    Envía la consulta del cliente al LLM (Groq / Llama-3.1-8b) a través de llm_service.py.
    """
    try:
        respuesta_bot = await generar_respuesta_llm(prompt_usuario=payload.mensaje)
        return ChatResponse(respuesta=respuesta_bot)

    except Exception as e:
        logger.error(f"Error en chat Guache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al procesar la consulta con el asistente virtual."
        )


# ------------------------------------------------------------------
# ARCHIVOS ESTÁTICOS (DEBE SER LA ÚLTIMA RUTA DECLARADA)
# ------------------------------------------------------------------
# Servir la interfaz web desde la carpeta web/
app.mount("/", StaticFiles(directory="web", html=True), name="web")