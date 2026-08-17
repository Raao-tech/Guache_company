"""crear tabla cotizaciones

Revision ID: 562276412be9
Revises: 
Create Date: 2026-08-17 17:40:40.672356

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '562276412be9'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "cotizaciones",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("folio", sa.String(), unique=True, index=True),
        sa.Column("nombre_contacto", sa.String(), index=True),
        sa.Column("telefono", sa.String()),
        sa.Column("empresa", sa.String(), nullable=True),
        sa.Column("sku_producto", sa.String(), index=True),
        sa.Column("cantidad_toneladas", sa.Float()),
        sa.Column("destino_despacho", sa.String()),
        sa.Column("observaciones", sa.String(), nullable=True),
        sa.Column("fecha_registro", sa.DateTime()),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("cotizaciones")
