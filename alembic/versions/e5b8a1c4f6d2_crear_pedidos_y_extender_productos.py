"""crear pedidos/pedido_items y extender productos_detal y usuarios

Revision ID: e5b8a1c4f6d2
Revises: a1c9f3e7d2b4
Create Date: 2026-08-27 17:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5b8a1c4f6d2'
down_revision: Union[str, Sequence[str], None] = 'a1c9f3e7d2b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("productos_detal", sa.Column("stock", sa.Integer(), nullable=True))
    op.add_column(
        "productos_detal",
        sa.Column("disponible_venezuela", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "productos_detal",
        sa.Column("disponible_espana", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.add_column(
        "usuarios", sa.Column("permiso_pedidos", sa.Boolean(), nullable=False, server_default=sa.false())
    )

    op.create_table(
        "pedidos",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("numero_pedido", sa.String(), nullable=False),
        sa.Column("mercado", sa.String(), nullable=False),
        sa.Column("metodo_pago", sa.String(), nullable=False),
        sa.Column("estado", sa.String(), nullable=False, server_default="pendiente_pago"),
        sa.Column("moneda", sa.String(), nullable=False),
        sa.Column("total", sa.Float(), nullable=False),
        sa.Column("nombre_cliente", sa.String(), nullable=False),
        sa.Column("email_cliente", sa.String(), nullable=False),
        sa.Column("telefono_cliente", sa.String(), nullable=False),
        sa.Column("direccion_entrega", sa.Text(), nullable=False),
        sa.Column("notas_cliente", sa.Text(), nullable=True),
        sa.Column("referencia_pago", sa.String(), nullable=True),
        sa.Column("comprobante_url", sa.String(), nullable=True),
        sa.Column("stripe_session_id", sa.String(), nullable=True),
        sa.Column("stripe_payment_intent_id", sa.String(), nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=True),
        sa.Column("fecha_actualizacion", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_pedidos_numero_pedido", "pedidos", ["numero_pedido"], unique=True)
    op.create_index("ix_pedidos_estado", "pedidos", ["estado"])
    op.create_index("ix_pedidos_mercado", "pedidos", ["mercado"])
    op.create_index("ix_pedidos_stripe_session_id", "pedidos", ["stripe_session_id"])

    op.create_table(
        "pedido_items",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("pedido_id", sa.Integer(), sa.ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "producto_id",
            sa.Integer(),
            sa.ForeignKey("productos_detal.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("nombre_producto", sa.String(), nullable=False),
        sa.Column("precio_unitario", sa.Float(), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("subtotal", sa.Float(), nullable=False),
        sa.Column("stock_reservado", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_pedido_items_pedido_id", "pedido_items", ["pedido_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_pedido_items_pedido_id", table_name="pedido_items")
    op.drop_table("pedido_items")

    op.drop_index("ix_pedidos_stripe_session_id", table_name="pedidos")
    op.drop_index("ix_pedidos_mercado", table_name="pedidos")
    op.drop_index("ix_pedidos_estado", table_name="pedidos")
    op.drop_index("ix_pedidos_numero_pedido", table_name="pedidos")
    op.drop_table("pedidos")

    with op.batch_alter_table("usuarios") as batch_op:
        batch_op.drop_column("permiso_pedidos")

    with op.batch_alter_table("productos_detal") as batch_op:
        batch_op.drop_column("disponible_espana")
        batch_op.drop_column("disponible_venezuela")
        batch_op.drop_column("stock")
