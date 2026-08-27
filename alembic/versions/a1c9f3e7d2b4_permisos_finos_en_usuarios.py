"""permisos finos en usuarios (reemplaza columna rol)

Revision ID: a1c9f3e7d2b4
Revises: 7796801640c3
Create Date: 2026-08-27 16:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c9f3e7d2b4'
down_revision: Union[str, Sequence[str], None] = '7796801640c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PERMISOS = ["productos", "blog", "asistente", "conversaciones", "usuarios"]


def upgrade() -> None:
    """Upgrade schema."""
    for permiso in PERMISOS:
        op.add_column(
            "usuarios",
            sa.Column(f"permiso_{permiso}", sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    usuarios = sa.table(
        "usuarios",
        sa.column("rol", sa.String()),
        *[sa.column(f"permiso_{p}", sa.Boolean()) for p in PERMISOS],
    )

    # rol="admin" -> los 5 permisos. rol="asistente" -> todos menos "usuarios"
    # (mismo comportamiento que tenía antes, solo que ahora explícito por columna).
    op.execute(
        usuarios.update()
        .where(usuarios.c.rol == "admin")
        .values({f"permiso_{p}": True for p in PERMISOS})
    )
    op.execute(
        usuarios.update()
        .where(usuarios.c.rol == "asistente")
        .values({f"permiso_{p}": True for p in PERMISOS if p != "usuarios"})
    )

    with op.batch_alter_table("usuarios") as batch_op:
        batch_op.drop_column("rol")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "usuarios", sa.Column("rol", sa.String(), nullable=False, server_default="asistente")
    )

    usuarios = sa.table(
        "usuarios",
        sa.column("rol", sa.String()),
        sa.column("permiso_usuarios", sa.Boolean()),
    )
    op.execute(usuarios.update().where(usuarios.c.permiso_usuarios.is_(True)).values(rol="admin"))

    with op.batch_alter_table("usuarios") as batch_op:
        for permiso in PERMISOS:
            batch_op.drop_column(f"permiso_{permiso}")
