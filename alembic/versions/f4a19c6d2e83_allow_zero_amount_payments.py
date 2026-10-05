"""allow zero-amount payment attempts

Revision ID: f4a19c6d2e83
Revises: b3f7c4d91a20
"""

from collections.abc import Sequence

from alembic import op


revision: str = "f4a19c6d2e83"
down_revision: str | Sequence[str] | None = "b3f7c4d91a20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_payments_amount_positive", "payments", type_="check")
    op.create_check_constraint(
        "ck_payments_amount_nonnegative", "payments", "amount >= 0"
    )


def downgrade() -> None:
    op.drop_constraint("ck_payments_amount_nonnegative", "payments", type_="check")
    op.create_check_constraint("ck_payments_amount_positive", "payments", "amount > 0")
