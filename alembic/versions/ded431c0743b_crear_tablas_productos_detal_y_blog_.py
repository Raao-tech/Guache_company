"""crear tablas productos_detal y blog_posts

Revision ID: ded431c0743b
Revises: 562276412be9
Create Date: 2026-08-19 21:27:14.376154

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ded431c0743b'
down_revision: Union[str, Sequence[str], None] = '562276412be9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "productos_detal",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("descripcion", sa.String(), nullable=False),
        sa.Column("precio", sa.Float(), nullable=True),
        sa.Column("moneda", sa.String(), nullable=True),
        sa.Column("imagen_url", sa.String(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=True),
        sa.Column("fecha_actualizacion", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "blog_posts",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("titulo", sa.String(), nullable=False),
        sa.Column("resumen", sa.String(), nullable=False),
        sa.Column("contenido", sa.Text(), nullable=False),
        sa.Column("audiencia", sa.String(), nullable=True),
        sa.Column("imagen_url", sa.String(), nullable=True),
        sa.Column("publicado", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("fecha_publicacion", sa.DateTime(), nullable=True),
        sa.Column("fecha_actualizacion", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_blog_posts_slug", "blog_posts", ["slug"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_blog_posts_slug", table_name="blog_posts")
    op.drop_table("blog_posts")
    op.drop_table("productos_detal")
