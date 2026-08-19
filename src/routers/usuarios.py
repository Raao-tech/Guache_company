from datetime import datetime
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import UsuarioDB, get_db
from src.routers.admin_auth import require_full_admin_role

router = APIRouter(prefix="/api/admin/usuarios", tags=["Administración"])


def hashear_clave(clave: str) -> str:
    return bcrypt.hashpw(clave.encode(), bcrypt.gensalt()).decode()


class UsuarioIn(BaseModel):
    username: str = Field(..., min_length=2)
    clave: str = Field(..., min_length=4)
    rol: str = Field(..., pattern="^(admin|asistente)$")
    activo: bool = True


class UsuarioUpdate(BaseModel):
    rol: str = Field(..., pattern="^(admin|asistente)$")
    activo: bool = True
    clave: Optional[str] = Field(None, min_length=4)  # solo si se quiere cambiar


class UsuarioOut(BaseModel):
    id: int
    username: str
    rol: str
    activo: bool
    fecha_creacion: Optional[datetime] = None

    model_config = {"from_attributes": True}


# Todas las rutas acá requieren rol admin completo — un asistente no
# puede ver ni gestionar esta lista.
@router.get("", response_model=list[UsuarioOut])
async def listar_usuarios(
    db: Session = Depends(get_db), _admin: None = Depends(require_full_admin_role)
):
    return db.query(UsuarioDB).order_by(UsuarioDB.username).all()


@router.post("", response_model=UsuarioOut)
async def crear_usuario(
    payload: UsuarioIn,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_full_admin_role),
):
    existe = db.query(UsuarioDB).filter(UsuarioDB.username == payload.username).first()
    if existe:
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese nombre.")

    usuario = UsuarioDB(
        username=payload.username,
        password_hash=hashear_clave(payload.clave),
        rol=payload.rol,
        activo=payload.activo,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.put("/{usuario_id}", response_model=UsuarioOut)
async def actualizar_usuario(
    usuario_id: int,
    payload: UsuarioUpdate,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_full_admin_role),
):
    usuario = db.get(UsuarioDB, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    usuario.rol = payload.rol
    usuario.activo = payload.activo
    if payload.clave:
        usuario.password_hash = hashear_clave(payload.clave)

    db.commit()
    db.refresh(usuario)
    return usuario


@router.delete("/{usuario_id}")
async def eliminar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_full_admin_role),
):
    usuario = db.get(UsuarioDB, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    db.delete(usuario)
    db.commit()
    return {"exito": True}
