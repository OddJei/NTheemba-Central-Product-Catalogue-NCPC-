"""Persist evidence-backed brand organization relationships.

Revision ID: a4e9b2c7d6f3
Revises: f1b7d3c5a8e2
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "a4e9b2c7d6f3"
down_revision: str | None = "f1b7d3c5a8e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("canonical_name", sa.String(length=240), nullable=False),
        sa.Column("normalized_name", sa.String(length=240), nullable=False, unique=True),
        sa.Column("lifecycle", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "brand_organization_relationships",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("brand_id", sa.String(length=36), sa.ForeignKey("brands.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("relationship_type", sa.String(length=64), nullable=False),
        sa.Column("evidence_source_id", sa.String(length=36), sa.ForeignKey("evidence_sources.id", ondelete="RESTRICT")),
        sa.Column("verification_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("brand_id", "organization_id", "relationship_type", name="uq_brand_organization_role"),
    )
    op.create_index("ix_brand_organization_relationships_brand_id", "brand_organization_relationships", ["brand_id"])
    op.create_index("ix_brand_organization_relationships_organization_id", "brand_organization_relationships", ["organization_id"])


def downgrade() -> None:
    op.drop_table("brand_organization_relationships")
    op.drop_table("organizations")
