"""Add customer authentication without changing existing customer/cart rows."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c9e21a4b870d"
down_revision: str | Sequence[str] | None = "f4a19c6d2e83"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "customers", sa.Column("password_hash", sa.String(255), nullable=True)
    )
    op.add_column(
        "customers",
        sa.Column("role", sa.String(20), server_default="customer", nullable=False),
    )
    op.add_column(
        "customers",
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.create_check_constraint(
        "ck_customers_role", "customers", "role IN ('customer', 'admin')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_customers_role", "customers", type_="check")
    op.drop_column("customers", "is_active")
    op.drop_column("customers", "role")
    op.drop_column("customers", "password_hash")
