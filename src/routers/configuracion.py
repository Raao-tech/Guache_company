from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import ConfiguracionDB, get_db
from src.routers.admin_auth import require_admin_session
from src.services.llm_service import CLAVE_SYSTEM_PROMPT, SYSTEM_PROMPT_POR_DEFECTO

router = APIRouter(prefix="/api/admin/configuracion", tags=["Administración"])


class PromptIn(BaseModel):
    prompt: str = Field(..., min_length=10)


@router.get("/prompt")
async def obtener_prompt(
    db: Session = Depends(get_db), _admin: None = Depends(require_admin_session)
):
    fila = db.query(ConfiguracionDB).filter(ConfiguracionDB.clave == CLAVE_SYSTEM_PROMPT).first()
    return {
        "prompt": fila.valor if fila else SYSTEM_PROMPT_POR_DEFECTO,
        "personalizado": fila is not None,
        "prompt_por_defecto": SYSTEM_PROMPT_POR_DEFECTO,
    }


@router.put("/prompt")
async def actualizar_prompt(
    payload: PromptIn,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin_session),
):
    fila = db.query(ConfiguracionDB).filter(ConfiguracionDB.clave == CLAVE_SYSTEM_PROMPT).first()
    if fila:
        fila.valor = payload.prompt
    else:
        fila = ConfiguracionDB(clave=CLAVE_SYSTEM_PROMPT, valor=payload.prompt)
        db.add(fila)
    db.commit()
    return {"exito": True}


@router.delete("/prompt")
async def restaurar_prompt_por_defecto(
    db: Session = Depends(get_db), _admin: None = Depends(require_admin_session)
):
    """Borra la personalización — vuelve a usar SYSTEM_PROMPT_POR_DEFECTO."""
    db.query(ConfiguracionDB).filter(ConfiguracionDB.clave == CLAVE_SYSTEM_PROMPT).delete()
    db.commit()
    return {"exito": True}
