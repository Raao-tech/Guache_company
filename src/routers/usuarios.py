from datetime import datetime
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import UsuarioDB, get_db
from src.routers.admin_auth import PERMISOS_DISPONIBLES, require_permission

router = APIRouter(prefix="/api/admin/usuarios", tags=["Administración"])


def hashear_clave(clave: str) -> str:
    return bcrypt.hashpw(clave.encode(), bcrypt.gensalt()).decode()


class PermisosIn(BaseModel):
    productos: bool = False
    blog: bool = False
    asistente: bool = False
    conversaciones: bool = False
    usuarios: bool = False
    pedidos: bool = False


class UsuarioIn(BaseModel):
    username: str = Field(..., min_length=2)
    clave: str = Field(..., min_length=4)
    permisos: PermisosIn = PermisosIn()
    activo: bool = True


class UsuarioUpdate(BaseModel):
    permisos: PermisosIn = PermisosIn()
    activo: bool = True
    clave: Optional[str] = Field(None, min_length=4)  # solo si se quiere cambiar


class UsuarioOut(BaseModel):
    id: int
    username: str
    permiso_productos: bool
    permiso_blog: bool
    permiso_asistente: bool
    permiso_conversaciones: bool
    permiso_usuarios: bool
    permiso_pedidos: bool
    activo: bool
    fecha_creacion: Optional[datetime] = None

    model_config = {"from_attributes": True}


def _aplicar_permisos(usuario: UsuarioDB, permisos: PermisosIn) -> None:
    for modulo in PERMISOS_DISPONIBLES:
        setattr(usuario, f"permiso_{modulo}", getattr(permisos, modulo))


# Todas las rutas acá requieren el permiso "usuarios" — quien lo tiene
# puede además otorgárselo a otra cuenta (equivale al viejo rol admin).
@router.get("", response_model=list[UsuarioOut])
async def listar_usuarios(
    db: Session = Depends(get_db), _admin: None = Depends(require_permission("usuarios"))
):
    return db.query(UsuarioDB).order_by(UsuarioDB.username).all()


@router.post("", response_model=UsuarioOut)
async def crear_usuario(
    payload: UsuarioIn,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_permission("usuarios")),
):
    existe = db.query(UsuarioDB).filter(UsuarioDB.username == payload.username).first()
    if existe:
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese nombre.")

    usuario = UsuarioDB(
        username=payload.username,
        password_hash=hashear_clave(payload.clave),
        activo=payload.activo,
    )
    _aplicar_permisos(usuario, payload.permisos)
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.put("/{usuario_id}", response_model=UsuarioOut)
async def actualizar_usuario(
    usuario_id: int,
    payload: UsuarioUpdate,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_permission("usuarios")),
):
    usuario = db.get(UsuarioDB, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    _aplicar_permisos(usuario, payload.permisos)
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
    _admin: None = Depends(require_permission("usuarios")),
):
    usuario = db.get(UsuarioDB, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    db.delete(usuario)
    db.commit()
    return {"exito": True}
