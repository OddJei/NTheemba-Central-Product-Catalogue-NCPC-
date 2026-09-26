"""Allow the explicit initial owner-authorized review outcome.

Revision ID: c9d1e4f7a2b6
Revises: b7c4d2e9f1a3
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c9d1e4f7a2b6"
down_revision: str | None = "b7c4d2e9f1a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("review_decisions") as batch:
        batch.alter_column("outcome", existing_type=sa.String(length=22), type_=sa.String(length=64), existing_nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("review_decisions") as batch:
        batch.alter_column("outcome", existing_type=sa.String(length=64), type_=sa.String(length=22), existing_nullable=False)
