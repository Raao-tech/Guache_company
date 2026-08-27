from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import ProductoDetalDB, get_db
from src.routers.admin_auth import require_permission

router = APIRouter(tags=["Detal"])


class ProductoDetalIn(BaseModel):
    nombre: str = Field(..., min_length=2)
    descripcion: str = Field(..., min_length=2)
    precio: Optional[float] = Field(None, ge=0)
    moneda: Optional[str] = None
    imagen_url: Optional[str] = None
    activo: bool = True
    orden: int = 0
    stock: Optional[int] = Field(None, ge=0)  # None = ilimitado/no rastreado
    disponible_venezuela: bool = True
    disponible_espana: bool = True


class ProductoDetalOut(ProductoDetalIn):
    id: int
    fecha_creacion: Optional[datetime] = None
    fecha_actualizacion: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- Público: lo que se muestra en la sección "Al Detal" de la web ---
@router.get("/api/detal/productos", response_model=list[ProductoDetalOut])
async def listar_productos_publico(db: Session = Depends(get_db)):
    return (
        db.query(ProductoDetalDB)
        .filter(ProductoDetalDB.activo.is_(True))
        .order_by(ProductoDetalDB.orden, ProductoDetalDB.id)
        .all()
    )


# --- Administración (requiere sesión) ---
@router.get(
    "/api/admin/productos",
    response_model=list[ProductoDetalOut],
    tags=["Administración"],
)
async def listar_productos_admin(
    db: Session = Depends(get_db), _admin: None = Depends(require_permission("productos"))
):
    return (
        db.query(ProductoDetalDB).order_by(ProductoDetalDB.orden, ProductoDetalDB.id).all()
    )


@router.post(
    "/api/admin/productos",
    response_model=ProductoDetalOut,
    tags=["Administración"],
)
async def crear_producto(
    payload: ProductoDetalIn,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_permission("productos")),
):
    producto = ProductoDetalDB(**payload.model_dump())
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto


@router.put(
    "/api/admin/productos/{producto_id}",
    response_model=ProductoDetalOut,
    tags=["Administración"],
)
async def actualizar_producto(
    producto_id: int,
    payload: ProductoDetalIn,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_permission("productos")),
):
    producto = db.get(ProductoDetalDB, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    for campo, valor in payload.model_dump().items():
        setattr(producto, campo, valor)

    db.commit()
    db.refresh(producto)
    return producto


@router.delete("/api/admin/productos/{producto_id}", tags=["Administración"])
async def eliminar_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_permission("productos")),
):
    producto = db.get(ProductoDetalDB, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    db.delete(producto)
    db.commit()
    return {"exito": True}
