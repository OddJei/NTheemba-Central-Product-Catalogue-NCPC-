"""Allow a published Class-B product family without an invented variant.

Revision ID: e2a8c4f6b9d1
Revises: c9d1e4f7a2b6
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "e2a8c4f6b9d1"
down_revision: str | None = "c9d1e4f7a2b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("publication_entries") as batch:
        batch.alter_column("variant_id", existing_type=sa.String(length=36), nullable=True)
        batch.alter_column("variant_version", existing_type=sa.Integer(), nullable=True)
    with op.batch_alter_table("seed_batch_items") as batch:
        batch.alter_column("variant_id", existing_type=sa.String(length=36), nullable=True)


def downgrade() -> None:
    connection = op.get_bind()
    has_product_only = connection.execute(
        sa.text("SELECT 1 FROM publication_entries WHERE variant_id IS NULL LIMIT 1")
    ).first()
    if has_product_only:
        raise RuntimeError("cannot downgrade while product-only publication entries exist")
    with op.batch_alter_table("publication_entries") as batch:
        batch.alter_column("variant_id", existing_type=sa.String(length=36), nullable=False)
        batch.alter_column("variant_version", existing_type=sa.Integer(), nullable=False)
    with op.batch_alter_table("seed_batch_items") as batch:
        batch.alter_column("variant_id", existing_type=sa.String(length=36), nullable=False)
