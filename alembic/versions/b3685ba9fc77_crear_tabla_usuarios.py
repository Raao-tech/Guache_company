"""crear tabla usuarios

Revision ID: b3685ba9fc77
Revises: ded431c0743b
Create Date: 2026-08-19 22:09:33.338260

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3685ba9fc77'
down_revision: Union[str, Sequence[str], None] = 'ded431c0743b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("rol", sa.String(), nullable=False, server_default="asistente"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_usuarios_username", "usuarios", ["username"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_usuarios_username", table_name="usuarios")
    op.drop_table("usuarios")
