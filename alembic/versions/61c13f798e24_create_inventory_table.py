"""create inventory table

Revision ID: 61c13f798e24
Revises: 8ecea52416d2
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "61c13f798e24"
down_revision: str | Sequence[str] | None = "8ecea52416d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "inventory",
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.CheckConstraint("quantity >= 0", name="ck_inventory_quantity_nonnegative"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("product_id"),
    )


def downgrade() -> None:
    op.drop_table("inventory")
