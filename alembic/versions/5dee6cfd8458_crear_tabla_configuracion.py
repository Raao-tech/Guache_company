"""crear tabla configuracion

Revision ID: 5dee6cfd8458
Revises: b3685ba9fc77
Create Date: 2026-08-26 19:56:07.394541

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5dee6cfd8458'
down_revision: Union[str, Sequence[str], None] = 'b3685ba9fc77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "configuracion",
        sa.Column("clave", sa.String(), primary_key=True),
        sa.Column("valor", sa.Text(), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("configuracion")
