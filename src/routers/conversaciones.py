from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database import MensajeChatDB, get_db
from src.routers.admin_auth import require_permission

router = APIRouter(prefix="/api/admin/conversaciones", tags=["Administración"])


class MensajeOut(BaseModel):
    rol: str
    contenido: str
    fecha: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ConversacionResumen(BaseModel):
    sesion_id: str
    canal: str
    cantidad_mensajes: int
    ultimo_mensaje: str
    fecha_ultimo_mensaje: Optional[datetime]


@router.get("", response_model=list[ConversacionResumen])
async def listar_conversaciones(
    db: Session = Depends(get_db), _admin: None = Depends(require_permission("conversaciones"))
):
    # Se agrupa en Python, no con GROUP BY: a esta escala (una agroindustria
    # con tráfico moderado) es más simple y portable entre SQLite/Postgres
    # que reconstruir "último mensaje por sesión" en SQL. Si el volumen
    # crece mucho, esto es lo primero que habría que optimizar.
    mensajes = db.query(MensajeChatDB).order_by(MensajeChatDB.fecha).all()

    resumenes: dict[str, ConversacionResumen] = {}
    for m in mensajes:
        previo = resumenes.get(m.sesion_id)
        resumenes[m.sesion_id] = ConversacionResumen(
            sesion_id=m.sesion_id,
            canal=m.canal,
            cantidad_mensajes=(previo.cantidad_mensajes + 1) if previo else 1,
            ultimo_mensaje=m.contenido,
            fecha_ultimo_mensaje=m.fecha,
        )

    return sorted(
        resumenes.values(),
        key=lambda r: r.fecha_ultimo_mensaje or datetime.min,
        reverse=True,
    )


@router.get("/{sesion_id}", response_model=list[MensajeOut])
async def obtener_conversacion(
    sesion_id: str,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_permission("conversaciones")),
):
    return (
        db.query(MensajeChatDB)
        .filter(MensajeChatDB.sesion_id == sesion_id)
        .order_by(MensajeChatDB.fecha)
        .all()
    )
