"""Record idempotency keys for direct business coverage links.

Revision ID: b2c7d9e1f4a6
Revises: a4e9b2c7d6f3
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b2c7d9e1f4a6"
down_revision: str | None = "a4e9b2c7d6f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "business_coverages",
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_business_coverages_idempotency_key",
        "business_coverages",
        ["idempotency_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_business_coverages_idempotency_key", table_name="business_coverages")
    op.drop_column("business_coverages", "idempotency_key")
