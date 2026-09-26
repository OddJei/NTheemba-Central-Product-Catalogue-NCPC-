"""Prevent duplicate product-only identities in one public release.

Revision ID: f1b7d3c5a8e2
Revises: e2a8c4f6b9d1
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "f1b7d3c5a8e2"
down_revision: str | None = "e2a8c4f6b9d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_snapshot_product_only",
        "publication_entries",
        ["snapshot_id", "product_id"],
        unique=True,
        postgresql_where=sa.text("variant_id IS NULL"),
        sqlite_where=sa.text("variant_id IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_snapshot_product_only", table_name="publication_entries")
