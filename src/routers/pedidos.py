import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import update
from sqlalchemy.orm import Session

from src.database import PedidoDB, PedidoItemDB, ProductoDetalDB, get_db
from src.routers.admin_auth import require_permission

router = APIRouter()

ESTADOS_PEDIDO = ["pendiente_pago", "pagado", "cancelado"]

# Métodos de pago válidos por mercado. Venezuela son los 3 confirmados a
# mano por un admin; España es únicamente Stripe (automático, ver Fase 2).
METODOS_POR_MERCADO = {
    "venezuela": ["pago_movil_ves", "zelle_usd", "usdt"],
    "espana": ["stripe"],
}


# ------------------------------------------------------------------
# Esquemas
# ------------------------------------------------------------------
class ItemCarritoIn(BaseModel):
    producto_id: int
    cantidad: int = Field(..., ge=1)


class PedidoCrearIn(BaseModel):
    mercado: str = Field(..., pattern="^(venezuela|espana)$")
    metodo_pago: str
    nombre_cliente: str = Field(..., min_length=2)
    email_cliente: str = Field(..., min_length=3)
    telefono_cliente: str = Field(..., min_length=4)
    direccion_entrega: str = Field(..., min_length=5)
    notas_cliente: Optional[str] = None
    referencia_pago: Optional[str] = None  # requerida si mercado="venezuela", ver crear_pedido
    items: list[ItemCarritoIn] = Field(..., min_length=1)


class PedidoCrearOut(BaseModel):
    numero_pedido: str
    estado: str
    mercado: str
    metodo_pago: str
    moneda: str
    total: float

    model_config = {"from_attributes": True}


class PedidoItemOut(BaseModel):
    nombre_producto: str
    precio_unitario: float
    cantidad: int
    subtotal: float

    model_config = {"from_attributes": True}


class PedidoPublicoOut(BaseModel):
    """
    Respuesta de la página pública de seguimiento — deliberadamente sin
    PII (sin teléfono, dirección ni referencia de pago), eso solo se ve
    en el panel admin. numero_pedido es el único control de acceso acá,
    por eso se genera con entropía real (ver _generar_numero_pedido).
    """

    numero_pedido: str
    estado: str
    mercado: str
    moneda: str
    total: float
    fecha_creacion: Optional[datetime] = None
    items: list[PedidoItemOut]

    model_config = {"from_attributes": True}


class PedidoAdminListItemOut(BaseModel):
    id: int
    numero_pedido: str
    mercado: str
    metodo_pago: str
    estado: str
    moneda: str
    total: float
    nombre_cliente: str
    fecha_creacion: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PedidoAdminDetalleOut(PedidoAdminListItemOut):
    email_cliente: str
    telefono_cliente: str
    direccion_entrega: str
    notas_cliente: Optional[str] = None
    referencia_pago: Optional[str] = None
    stripe_session_id: Optional[str] = None
    items: list[PedidoItemOut]


# ------------------------------------------------------------------
# Helpers de stock — ver decisión de diseño 4 del plan: se reserva al
# crear el pedido (no al confirmar el pago), con un UPDATE atómico y
# condicional para que dos checkouts concurrentes no vendan el mismo
# stock dos veces, sin necesitar locks explícitos.
# ------------------------------------------------------------------
def _generar_numero_pedido() -> str:
    return f"PED-{datetime.now().year}-{uuid.uuid4().hex[:16].upper()}"


def _reservar_stock(db: Session, producto: ProductoDetalDB, cantidad: int) -> bool:
    """Devuelve True si efectivamente descontó stock (False si el producto no lo rastrea)."""
    if producto.stock is None:
        return False
    resultado = db.execute(
        update(ProductoDetalDB)
        .where(ProductoDetalDB.id == producto.id, ProductoDetalDB.stock >= cantidad)
        .values(stock=ProductoDetalDB.stock - cantidad)
    )
    if resultado.rowcount == 0:
        raise HTTPException(status_code=400, detail=f"No hay suficiente stock de '{producto.nombre}'.")
    return True


def _restaurar_stock(db: Session, pedido: PedidoDB) -> None:
    for item in pedido.items:
        if item.stock_reservado and item.producto_id is not None:
            db.execute(
                update(ProductoDetalDB)
                .where(ProductoDetalDB.id == item.producto_id)
                .values(stock=ProductoDetalDB.stock + item.cantidad)
            )


def _cancelar_pedido_y_restaurar_stock(db: Session, pedido: PedidoDB) -> None:
    """
    Idempotente a propósito: la reutiliza el webhook de Stripe (Fase 2),
    que puede reenviar el mismo evento más de una vez.
    """
    if pedido.estado != "pendiente_pago":
        return
    _restaurar_stock(db, pedido)
    pedido.estado = "cancelado"
    db.commit()


# ------------------------------------------------------------------
# Checkout público (sin cuenta de cliente)
# ------------------------------------------------------------------
@router.post("/api/tienda/pedidos", response_model=PedidoCrearOut, tags=["Tienda"])
async def crear_pedido(payload: PedidoCrearIn, db: Session = Depends(get_db)):
    metodos_validos = METODOS_POR_MERCADO[payload.mercado]
    if payload.metodo_pago not in metodos_validos:
        raise HTTPException(
            status_code=400,
            detail=f"Método de pago inválido para {payload.mercado}. Válidos: {', '.join(metodos_validos)}.",
        )
    if payload.mercado == "venezuela" and not payload.referencia_pago:
        raise HTTPException(status_code=400, detail="Falta la referencia de pago.")

    campo_disponible = "disponible_venezuela" if payload.mercado == "venezuela" else "disponible_espana"

    # Primera pasada: solo lectura/validación, nada se escribe todavía.
    productos_por_id: dict[int, ProductoDetalDB] = {}
    monedas = set()
    for item in payload.items:
        producto = db.get(ProductoDetalDB, item.producto_id)
        if not producto or not producto.activo or not getattr(producto, campo_disponible):
            raise HTTPException(status_code=400, detail=f"Producto {item.producto_id} no disponible.")
        if producto.precio is None or not producto.moneda:
            raise HTTPException(status_code=400, detail=f"'{producto.nombre}' no tiene precio configurado.")
        productos_por_id[item.producto_id] = producto
        monedas.add(producto.moneda)

    if len(monedas) > 1:
        raise HTTPException(
            status_code=400, detail="El carrito no puede mezclar productos en distintas monedas."
        )
    moneda = monedas.pop()

    # Segunda pasada: reserva de stock ítem por ítem. Si algo falla a
    # mitad de camino, se revierte todo lo reservado hasta ahí (nada se
    # comprometió con commit todavía) antes de relanzar el error.
    items_pedido: list[PedidoItemDB] = []
    total = 0.0
    try:
        for item in payload.items:
            producto = productos_por_id[item.producto_id]
            reservado = _reservar_stock(db, producto, item.cantidad)
            subtotal = producto.precio * item.cantidad
            total += subtotal
            items_pedido.append(
                PedidoItemDB(
                    producto_id=producto.id,
                    nombre_producto=producto.nombre,
                    precio_unitario=producto.precio,
                    cantidad=item.cantidad,
                    subtotal=subtotal,
                    stock_reservado=reservado,
                )
            )
    except HTTPException:
        db.rollback()
        raise

    pedido = PedidoDB(
        numero_pedido=_generar_numero_pedido(),
        mercado=payload.mercado,
        metodo_pago=payload.metodo_pago,
        estado="pendiente_pago",
        moneda=moneda,
        total=total,
        nombre_cliente=payload.nombre_cliente,
        email_cliente=payload.email_cliente,
        telefono_cliente=payload.telefono_cliente,
        direccion_entrega=payload.direccion_entrega,
        notas_cliente=payload.notas_cliente,
        referencia_pago=payload.referencia_pago if payload.mercado == "venezuela" else None,
    )
    pedido.items = items_pedido
    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    return pedido


@router.get("/api/tienda/pedidos/{numero_pedido}", response_model=PedidoPublicoOut, tags=["Tienda"])
async def obtener_pedido_publico(numero_pedido: str, db: Session = Depends(get_db)):
    pedido = db.query(PedidoDB).filter(PedidoDB.numero_pedido == numero_pedido).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")
    return pedido


# ------------------------------------------------------------------
# Administración (requiere permiso "pedidos")
# ------------------------------------------------------------------
@router.get(
    "/api/admin/pedidos", response_model=list[PedidoAdminListItemOut], tags=["Administración"]
)
async def listar_pedidos_admin(
    estado: Optional[str] = None,
    mercado: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_permission("pedidos")),
):
    query = db.query(PedidoDB)
    if estado:
        query = query.filter(PedidoDB.estado == estado)
    if mercado:
        query = query.filter(PedidoDB.mercado == mercado)
    return query.order_by(PedidoDB.fecha_creacion.desc()).all()


@router.get(
    "/api/admin/pedidos/{pedido_id}",
    response_model=PedidoAdminDetalleOut,
    tags=["Administración"],
)
async def obtener_pedido_admin(
    pedido_id: int,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_permission("pedidos")),
):
    pedido = db.get(PedidoDB, pedido_id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")
    return pedido


@router.post(
    "/api/admin/pedidos/{pedido_id}/confirmar",
    response_model=PedidoAdminListItemOut,
    tags=["Administración"],
)
async def confirmar_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_permission("pedidos")),
):
    pedido = db.get(PedidoDB, pedido_id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")
    if pedido.estado != "pendiente_pago":
        raise HTTPException(status_code=400, detail=f"El pedido ya está en estado '{pedido.estado}'.")

    pedido.estado = "pagado"
    db.commit()
    db.refresh(pedido)
    return pedido


@router.post(
    "/api/admin/pedidos/{pedido_id}/cancelar",
    response_model=PedidoAdminListItemOut,
    tags=["Administración"],
)
async def cancelar_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_permission("pedidos")),
):
    pedido = db.get(PedidoDB, pedido_id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")
    if pedido.estado != "pendiente_pago":
        raise HTTPException(status_code=400, detail=f"El pedido ya está en estado '{pedido.estado}'.")

    _cancelar_pedido_y_restaurar_stock(db, pedido)
    db.refresh(pedido)
    return pedido
