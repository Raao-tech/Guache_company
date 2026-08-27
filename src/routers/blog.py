import re
import unicodedata
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import BlogPostDB, get_db
from src.routers.admin_auth import require_permission

router = APIRouter(tags=["Blog"])


def generar_slug(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = texto.lower()
    texto = re.sub(r"[^a-z0-9]+", "-", texto).strip("-")
    return texto or "articulo"


def slug_unico(db: Session, base_slug: str, excluir_id: Optional[int] = None) -> str:
    slug = base_slug
    contador = 2
    while True:
        query = db.query(BlogPostDB).filter(BlogPostDB.slug == slug)
        if excluir_id is not None:
            query = query.filter(BlogPostDB.id != excluir_id)
        if not query.first():
            return slug
        slug = f"{base_slug}-{contador}"
        contador += 1


class BlogPostIn(BaseModel):
    titulo: str = Field(..., min_length=2)
    resumen: str = Field(..., min_length=2)
    contenido: str = Field(..., min_length=2)
    audiencia: Optional[str] = None
    imagen_url: Optional[str] = None
    publicado: bool = True


class BlogPostOut(BlogPostIn):
    id: int
    slug: str
    fecha_publicacion: Optional[datetime] = None
    fecha_actualizacion: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- Público ---
@router.get("/api/blog/posts", response_model=list[BlogPostOut])
async def listar_posts_publico(db: Session = Depends(get_db)):
    return (
        db.query(BlogPostDB)
        .filter(BlogPostDB.publicado.is_(True))
        .order_by(BlogPostDB.fecha_publicacion.desc())
        .all()
    )


@router.get("/api/blog/posts/{slug}", response_model=BlogPostOut)
async def obtener_post_publico(slug: str, db: Session = Depends(get_db)):
    post = (
        db.query(BlogPostDB)
        .filter(BlogPostDB.slug == slug, BlogPostDB.publicado.is_(True))
        .first()
    )
    if not post:
        raise HTTPException(status_code=404, detail="Artículo no encontrado.")
    return post


# --- Administración (requiere sesión) ---
@router.get("/api/admin/blog", response_model=list[BlogPostOut], tags=["Administración"])
async def listar_posts_admin(
    db: Session = Depends(get_db), _admin: None = Depends(require_permission("blog"))
):
    return db.query(BlogPostDB).order_by(BlogPostDB.fecha_publicacion.desc()).all()


@router.get(
    "/api/admin/blog/{post_id}", response_model=BlogPostOut, tags=["Administración"]
)
async def obtener_post_admin(
    post_id: int,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_permission("blog")),
):
    post = db.get(BlogPostDB, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Artículo no encontrado.")
    return post


@router.post("/api/admin/blog", response_model=BlogPostOut, tags=["Administración"])
async def crear_post(
    payload: BlogPostIn,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_permission("blog")),
):
    slug = slug_unico(db, generar_slug(payload.titulo))
    post = BlogPostDB(**payload.model_dump(), slug=slug)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.put(
    "/api/admin/blog/{post_id}", response_model=BlogPostOut, tags=["Administración"]
)
async def actualizar_post(
    post_id: int,
    payload: BlogPostIn,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_permission("blog")),
):
    post = db.get(BlogPostDB, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Artículo no encontrado.")

    # El slug no cambia al editar el título — mantiene estables los links ya compartidos.
    for campo, valor in payload.model_dump().items():
        setattr(post, campo, valor)

    db.commit()
    db.refresh(post)
    return post


@router.delete("/api/admin/blog/{post_id}", tags=["Administración"])
async def eliminar_post(
    post_id: int,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_permission("blog")),
):
    post = db.get(BlogPostDB, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Artículo no encontrado.")

    db.delete(post)
    db.commit()
    return {"exito": True}
