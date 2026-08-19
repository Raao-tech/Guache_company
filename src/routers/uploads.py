import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from src.routers.admin_auth import require_admin_session

router = APIRouter(prefix="/api/admin", tags=["Administración"])

UPLOAD_DIR = Path("web/uploads")
MAX_UPLOAD_SIZE = 2 * 1024 * 1024  # 2 MB — el VPS tiene poco espacio libre en disco

# La extensión se decide a partir del content-type validado, nunca del
# nombre de archivo que manda el cliente (evita path traversal / extensiones
# peligrosas disfrazadas de imagen).
CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


@router.post("/upload")
async def subir_imagen(
    archivo: UploadFile = File(...),
    _admin: None = Depends(require_admin_session),
):
    extension = CONTENT_TYPE_EXTENSIONS.get(archivo.content_type)
    if extension is None:
        raise HTTPException(
            status_code=400,
            detail="Formato de imagen no soportado. Usá JPG, PNG, WEBP o GIF.",
        )

    contenido = await archivo.read()
    if len(contenido) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail="La imagen supera el tamaño máximo permitido (2 MB).",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    nombre_archivo = f"{uuid.uuid4().hex}{extension}"
    (UPLOAD_DIR / nombre_archivo).write_bytes(contenido)

    return {"url": f"/uploads/{nombre_archivo}"}
