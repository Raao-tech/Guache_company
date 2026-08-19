import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from src import config

router = APIRouter(prefix="/api/admin", tags=["Administración"])


def require_admin_session(request: Request) -> None:
    """
    Protege las rutas del panel de administración con la sesión creada
    en /api/admin/login (cookie firmada, ver SessionMiddleware en main.py).
    Distinto de `verificar_admin` (HTTP Basic) que sigue protegiendo
    GET /api/cotizaciones — ambos validan contra las mismas credenciales
    de administrador, es la misma persona/cuenta.
    """
    if not request.session.get("admin"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado. Iniciá sesión en /admin/login.",
        )


class LoginRequest(BaseModel):
    usuario: str = Field(..., min_length=1)
    clave: str = Field(..., min_length=1)


@router.post("/login")
async def login(payload: LoginRequest, request: Request):
    usuario_ok = secrets.compare_digest(payload.usuario, config.ADMIN_USERNAME)
    clave_ok = secrets.compare_digest(payload.clave, config.ADMIN_PASSWORD)
    if not (usuario_ok and clave_ok):
        raise HTTPException(status_code=401, detail="Usuario o clave incorrectos.")

    request.session["admin"] = True
    return {"exito": True}


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"exito": True}


@router.get("/whoami")
async def whoami(request: Request):
    return {"autenticado": bool(request.session.get("admin"))}
