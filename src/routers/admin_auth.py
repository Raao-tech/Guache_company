import secrets

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src import config
from src.database import UsuarioDB, get_db

router = APIRouter(prefix="/api/admin", tags=["Administración"])


def require_admin_session(request: Request) -> None:
    """
    Protege las rutas del panel de administración con la sesión creada
    en /api/admin/login (cookie firmada, ver SessionMiddleware en main.py).
    Cualquier usuario logueado pasa esto — para exigir además el
    permiso de un módulo puntual, ver `require_permission`.
    Distinto de `verificar_admin` (HTTP Basic) que sigue protegiendo
    GET /api/cotizaciones con la cuenta compartida de main.py.
    """
    if not request.session.get("admin"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado. Iniciá sesión en /admin/login.",
        )


PERMISOS_DISPONIBLES = ["productos", "blog", "asistente", "conversaciones", "usuarios"]


def require_permission(modulo: str):
    """
    Como `require_admin_session`, pero además exige el permiso del
    módulo indicado (uno de PERMISOS_DISPONIBLES) para el usuario
    logueado. Usarlo en las rutas de administración de cada módulo —
    ej. `Depends(require_permission("blog"))` en src/routers/blog.py.
    """

    def dependencia(request: Request) -> None:
        require_admin_session(request)
        permisos = request.session.get("permisos") or {}
        if not permisos.get(modulo):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Esta acción requiere el permiso '{modulo}'.",
            )

    return dependencia


class LoginRequest(BaseModel):
    usuario: str = Field(..., min_length=1)
    clave: str = Field(..., min_length=1)


@router.post("/login")
async def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    # 1. Cuenta compartida de respaldo (ADMIN_USERNAME/ADMIN_PASSWORD en .env) —
    # siempre tiene los 5 permisos, no depende de la tabla usuarios.
    if secrets.compare_digest(payload.usuario, config.ADMIN_USERNAME) and secrets.compare_digest(
        payload.clave, config.ADMIN_PASSWORD
    ):
        request.session["admin"] = True
        request.session["permisos"] = {p: True for p in PERMISOS_DISPONIBLES}
        request.session["username"] = payload.usuario
        return {"exito": True}

    # 2. Usuarios individuales (tabla usuarios)
    usuario = (
        db.query(UsuarioDB)
        .filter(UsuarioDB.username == payload.usuario, UsuarioDB.activo.is_(True))
        .first()
    )
    if usuario and bcrypt.checkpw(payload.clave.encode(), usuario.password_hash.encode()):
        request.session["admin"] = True
        request.session["permisos"] = {
            p: getattr(usuario, f"permiso_{p}") for p in PERMISOS_DISPONIBLES
        }
        request.session["username"] = usuario.username
        return {"exito": True}

    raise HTTPException(status_code=401, detail="Usuario o clave incorrectos.")


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"exito": True}


@router.get("/whoami")
async def whoami(request: Request):
    if not request.session.get("admin"):
        return {"autenticado": False}
    return {
        "autenticado": True,
        "username": request.session.get("username"),
        "permisos": request.session.get("permisos", {}),
    }
