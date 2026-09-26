"""NCPC seed batches and durable per-claim evidence ledger.

Revision ID: b7c4d2e9f1a3
Revises: 9ae61d0b4f72
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7c4d2e9f1a3"
down_revision: str | None = "5a8c2e9d7f41"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence_sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_key", sa.String(128), nullable=False, unique=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("authority", sa.String(64), nullable=False),
        sa.Column("accessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "catalogue_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("evidence_sources.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id", ondelete="RESTRICT")),
        sa.Column("variant_id", sa.String(36), sa.ForeignKey("variants.id", ondelete="RESTRICT")),
        sa.Column("claim_type", sa.String(64), nullable=False), sa.Column("claim_value", sa.Text(), nullable=False),
        sa.Column("evidence_tier", sa.String(32), nullable=False), sa.Column("confidence", sa.String(32), nullable=False),
        sa.Column("verification_status", sa.String(32), nullable=False), sa.Column("image_reference", sa.String(2048)), sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("product_id IS NOT NULL OR variant_id IS NOT NULL", name="ck_catalogue_evidence_has_identity"),
    )
    op.create_index("ix_catalogue_evidence_source_id", "catalogue_evidence", ["source_id"])
    op.create_table(
        "seed_batches",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("public_id", sa.String(32), nullable=False, unique=True),
        sa.Column("manifest_hash", sa.String(64), nullable=False, unique=True), sa.Column("decision_type", sa.String(64), nullable=False),
        sa.Column("actor_label", sa.String(240), nullable=False), sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(96), sa.ForeignKey("api_clients.client_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("publication_id", sa.String(36), sa.ForeignKey("publication_snapshots.id", ondelete="RESTRICT")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "seed_batch_items",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("batch_id", sa.String(36), sa.ForeignKey("seed_batches.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("variant_id", sa.String(36), sa.ForeignKey("variants.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("review_case_id", sa.String(36), sa.ForeignKey("review_cases.id", ondelete="RESTRICT"), nullable=False, unique=True),
    )


def downgrade() -> None:
    op.drop_table("seed_batch_items")
    op.drop_table("seed_batches")
    op.drop_index("ix_catalogue_evidence_source_id", table_name="catalogue_evidence")
    op.drop_table("catalogue_evidence")
    op.drop_table("evidence_sources")
