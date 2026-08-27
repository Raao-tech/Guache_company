"""crear tabla mensajes_chat

Revision ID: 7796801640c3
Revises: 5dee6cfd8458
Create Date: 2026-08-27 15:34:32.838359

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7796801640c3'
down_revision: Union[str, Sequence[str], None] = '5dee6cfd8458'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "mensajes_chat",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("sesion_id", sa.String(), nullable=False),
        sa.Column("canal", sa.String(), nullable=False),
        sa.Column("rol", sa.String(), nullable=False),
        sa.Column("contenido", sa.Text(), nullable=False),
        sa.Column("fecha", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_mensajes_chat_sesion_id", "mensajes_chat", ["sesion_id"])
    op.create_index("ix_mensajes_chat_fecha", "mensajes_chat", ["fecha"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_mensajes_chat_fecha", table_name="mensajes_chat")
    op.drop_index("ix_mensajes_chat_sesion_id", table_name="mensajes_chat")
    op.drop_table("mensajes_chat")
