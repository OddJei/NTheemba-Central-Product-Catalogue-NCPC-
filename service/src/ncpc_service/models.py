from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    inspect,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .enums import (
    AliasState,
    ApprovalState,
    BarcodeState,
    CoverageState,
    ExposurePreference,
    LifecycleState,
    PrincipalRole,
    RelationshipType,
    ReviewOutcome,
    ReviewState,
    SnapshotState,
    SubmissionState,
    SubmissionType,
)

JSON_VALUE = JSON().with_variant(JSONB(), "postgresql")


def utc_now() -> datetime:
    return datetime.now(UTC)


def uuid_str() -> str:
    return str(uuid.uuid4())


def enum_column(enum_type: type, *, default: Any | None = None) -> Any:
    return mapped_column(
        Enum(enum_type, native_enum=False, values_callable=lambda items: [item.value for item in items]),
        default=default,
        nullable=False,
    )


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class IdSequence(Base):
    __tablename__ = "id_sequences"

    namespace: Mapped[str] = mapped_column(String(16), primary_key=True)
    next_value: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class ApiClient(Base, TimestampMixin):
    __tablename__ = "api_clients"

    client_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    token_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    role: Mapped[PrincipalRole] = enum_column(PrincipalRole)
    business_id: Mapped[str | None] = mapped_column(String(128), index=True)
    scopes: Mapped[list[str]] = mapped_column(JSON_VALUE, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Brand(Base, TimestampMixin):
    __tablename__ = "brands"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    canonical_name: Mapped[str] = mapped_column(String(240), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(240), unique=True, nullable=False)
    lifecycle: Mapped[LifecycleState] = enum_column(LifecycleState, default=LifecycleState.ACTIVE)


class Organization(Base, TimestampMixin):
    """A manufacturer, brand owner, or distributor; never a tenant business."""
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    canonical_name: Mapped[str] = mapped_column(String(240), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(240), unique=True, nullable=False)
    lifecycle: Mapped[LifecycleState] = enum_column(LifecycleState, default=LifecycleState.ACTIVE)


class BrandOrganizationRelationship(Base, TimestampMixin):
    """Evidence-backed brand relationship; never a shop or tenant assertion."""
    __tablename__ = "brand_organization_relationships"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id", ondelete="RESTRICT"), index=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"), index=True)
    relationship_type: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_source_id: Mapped[str | None] = mapped_column(ForeignKey("evidence_sources.id", ondelete="RESTRICT"))
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="VERIFIED")
    __table_args__ = (UniqueConstraint("brand_id", "organization_id", "relationship_type", name="uq_brand_organization_role"),)


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    canonical_name: Mapped[str] = mapped_column(String(240), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(240), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"))
    taxonomy_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    lifecycle: Mapped[LifecycleState] = enum_column(LifecycleState, default=LifecycleState.ACTIVE)

    __table_args__ = (UniqueConstraint("parent_id", "normalized_name", name="uq_category_parent_name"),)


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(320), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(320), index=True, nullable=False)
    brand_id: Mapped[str | None] = mapped_column(ForeignKey("brands.id", ondelete="RESTRICT"))
    category_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"))
    lifecycle: Mapped[LifecycleState] = enum_column(LifecycleState, default=LifecycleState.ACTIVE)
    approval_state: Mapped[ApprovalState] = enum_column(ApprovalState, default=ApprovalState.DRAFT)
    superseded_by_id: Mapped[str | None] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON_VALUE, default=dict)

    brand: Mapped[Brand | None] = relationship()
    category: Mapped[Category | None] = relationship()
    variants: Mapped[list[Variant]] = relationship(back_populates="product")

    __table_args__ = (
        CheckConstraint(
            "(lifecycle <> 'MERGED') OR (superseded_by_id IS NOT NULL)",
            name="ck_product_merged_has_survivor",
        ),
    )


class Variant(Base, TimestampMixin):
    __tablename__ = "variants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    canonical_name: Mapped[str] = mapped_column(String(320), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(320), index=True, nullable=False)
    pack_definition: Mapped[dict[str, Any]] = mapped_column(JSON_VALUE, default=dict)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON_VALUE, default=dict)
    lifecycle: Mapped[LifecycleState] = enum_column(LifecycleState, default=LifecycleState.ACTIVE)
    approval_state: Mapped[ApprovalState] = enum_column(ApprovalState, default=ApprovalState.DRAFT)
    superseded_by_id: Mapped[str | None] = mapped_column(ForeignKey("variants.id", ondelete="RESTRICT"))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON_VALUE, default=dict)

    product: Mapped[Product] = relationship(back_populates="variants", foreign_keys=[product_id])
    barcodes: Mapped[list[BarcodeClaim]] = relationship(back_populates="variant")

    __table_args__ = (
        CheckConstraint(
            "(lifecycle <> 'MERGED') OR (superseded_by_id IS NOT NULL)",
            name="ck_variant_merged_has_survivor",
        ),
    )


class Alias(Base, TimestampMixin):
    __tablename__ = "aliases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    display_text: Mapped[str] = mapped_column(String(320), nullable=False)
    normalized_text: Mapped[str] = mapped_column(String(320), index=True, nullable=False)
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    variant_id: Mapped[str | None] = mapped_column(ForeignKey("variants.id", ondelete="RESTRICT"))
    alias_kind: Mapped[str] = mapped_column(String(64), default="COMMON", nullable=False)
    language: Mapped[str | None] = mapped_column(String(16))
    state: Mapped[AliasState] = enum_column(AliasState, default=AliasState.PROPOSED)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON_VALUE, default=dict)

    __table_args__ = (
        CheckConstraint(
            "(product_id IS NOT NULL AND variant_id IS NULL) OR "
            "(product_id IS NULL AND variant_id IS NOT NULL)",
            name="ck_alias_exactly_one_target",
        ),
        UniqueConstraint("normalized_text", "product_id", "variant_id", name="uq_alias_target_normalized"),
    )


class BarcodeClaim(Base, TimestampMixin):
    __tablename__ = "barcode_claims"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    variant_id: Mapped[str] = mapped_column(ForeignKey("variants.id", ondelete="RESTRICT"), index=True)
    original_value: Mapped[str] = mapped_column(String(128), nullable=False)
    normalized_value: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    symbology: Mapped[str | None] = mapped_column(String(32))
    state: Mapped[BarcodeState] = enum_column(BarcodeState, default=BarcodeState.PROPOSED)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(256))
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON_VALUE, default=dict)
    conflict_group_id: Mapped[str | None] = mapped_column(String(36), index=True)
    replacement_claim_id: Mapped[str | None] = mapped_column(
        ForeignKey("barcode_claims.id", ondelete="RESTRICT")
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    variant: Mapped[Variant] = relationship(back_populates="barcodes", foreign_keys=[variant_id])

    __table_args__ = (
        Index(
            "uq_barcode_trusted_active",
            "normalized_value",
            unique=True,
            postgresql_where=(state == BarcodeState.VERIFIED_ACTIVE) & (active.is_(True)),
            sqlite_where=(state == BarcodeState.VERIFIED_ACTIVE) & (active.is_(True)),
        ),
    )


class Submission(Base, TimestampMixin):
    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    submission_type: Mapped[SubmissionType] = enum_column(SubmissionType)
    state: Mapped[SubmissionState] = enum_column(SubmissionState, default=SubmissionState.SUBMITTED)
    business_id: Mapped[str | None] = mapped_column(String(128), index=True)
    business_product_ref: Mapped[str | None] = mapped_column(String(128), index=True)
    target_product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    target_variant_id: Mapped[str | None] = mapped_column(ForeignKey("variants.id", ondelete="RESTRICT"))
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    submitter_client_id: Mapped[str] = mapped_column(
        ForeignKey("api_clients.client_id", ondelete="RESTRICT"), index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    previous_submission_id: Mapped[str | None] = mapped_column(
        ForeignKey("submissions.id", ondelete="RESTRICT")
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    changes: Mapped[list[ProposedChange]] = relationship(
        back_populates="submission", cascade="all, delete-orphan"
    )
    review_case: Mapped[ReviewCase | None] = relationship(back_populates="submission", uselist=False)

    __table_args__ = (
        UniqueConstraint("submitter_client_id", "idempotency_key", name="uq_submission_client_idempotency"),
    )


class ProposedChange(Base):
    __tablename__ = "proposed_changes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), index=True)
    field_path: Mapped[str] = mapped_column(String(160), nullable=False)
    old_value: Mapped[Any | None] = mapped_column(JSON_VALUE)
    proposed_value: Mapped[Any] = mapped_column(JSON_VALUE, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON_VALUE, default=dict)

    submission: Mapped[Submission] = relationship(back_populates="changes")


class ReviewCase(Base, TimestampMixin):
    __tablename__ = "review_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    submission_id: Mapped[str] = mapped_column(
        ForeignKey("submissions.id", ondelete="RESTRICT"), unique=True, index=True
    )
    reason: Mapped[str] = mapped_column(String(128), nullable=False)
    state: Mapped[ReviewState] = enum_column(ReviewState, default=ReviewState.OPEN)
    assigned_to: Mapped[str | None] = mapped_column(ForeignKey("api_clients.client_id", ondelete="RESTRICT"))

    submission: Mapped[Submission] = relationship(back_populates="review_case")
    decisions: Mapped[list[ReviewDecision]] = relationship(
        back_populates="review_case", cascade="all, delete-orphan"
    )


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    review_case_id: Mapped[str] = mapped_column(
        ForeignKey("review_cases.id", ondelete="RESTRICT"), index=True
    )
    reviewer_client_id: Mapped[str] = mapped_column(ForeignKey("api_clients.client_id", ondelete="RESTRICT"))
    outcome: Mapped[ReviewOutcome] = enum_column(ReviewOutcome)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON_VALUE, default=dict)
    decision_data: Mapped[dict[str, Any]] = mapped_column(JSON_VALUE, default=dict)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    review_case: Mapped[ReviewCase] = relationship(back_populates="decisions")


class EvidenceSource(Base, TimestampMixin):
    """An authoritative source reference; never stores copied artwork or shop facts."""
    __tablename__ = "evidence_sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    source_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048))
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    authority: Mapped[str] = mapped_column(String(64), nullable=False)
    accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class CatalogueEvidence(Base, TimestampMixin):
    """Per-claim provenance for an identity assertion."""
    __tablename__ = "catalogue_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    source_id: Mapped[str] = mapped_column(ForeignKey("evidence_sources.id", ondelete="RESTRICT"), index=True)
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    variant_id: Mapped[str | None] = mapped_column(ForeignKey("variants.id", ondelete="RESTRICT"), index=True)
    claim_type: Mapped[str] = mapped_column(String(64), nullable=False)
    claim_value: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_tier: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False)
    image_reference: Mapped[str | None] = mapped_column(String(2048))
    notes: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (CheckConstraint("product_id IS NOT NULL OR variant_id IS NOT NULL", name="ck_catalogue_evidence_has_identity"),)


class SeedBatch(Base, TimestampMixin):
    """A fingerprinted, owner-authorized initial seed; not a business submission."""
    __tablename__ = "seed_batches"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    manifest_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    decision_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_label: Mapped[str] = mapped_column(String(240), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("api_clients.client_id", ondelete="RESTRICT"), nullable=False)
    publication_id: Mapped[str | None] = mapped_column(ForeignKey("publication_snapshots.id", ondelete="RESTRICT"))


class SeedBatchItem(Base):
    __tablename__ = "seed_batch_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    batch_id: Mapped[str] = mapped_column(ForeignKey("seed_batches.id", ondelete="RESTRICT"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    variant_id: Mapped[str | None] = mapped_column(ForeignKey("variants.id", ondelete="RESTRICT"), unique=True, index=True)
    review_case_id: Mapped[str] = mapped_column(ForeignKey("review_cases.id", ondelete="RESTRICT"), unique=True)


class IdentityRelationship(Base):
    __tablename__ = "identity_relationships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    entity_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    source_product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    target_product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    source_variant_id: Mapped[str | None] = mapped_column(ForeignKey("variants.id", ondelete="RESTRICT"))
    target_variant_id: Mapped[str | None] = mapped_column(ForeignKey("variants.id", ondelete="RESTRICT"))
    relationship_type: Mapped[RelationshipType] = enum_column(RelationshipType)
    decision_id: Mapped[str] = mapped_column(ForeignKey("review_decisions.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        CheckConstraint(
            "(entity_kind = 'PRODUCT' AND source_product_id IS NOT NULL AND "
            "target_product_id IS NOT NULL AND source_variant_id IS NULL AND target_variant_id IS NULL) "
            "OR (entity_kind = 'VARIANT' AND source_variant_id IS NOT NULL AND "
            "target_variant_id IS NOT NULL AND source_product_id IS NULL AND target_product_id IS NULL)",
            name="ck_identity_relationship_kind",
        ),
    )


class BusinessCoverage(Base, TimestampMixin):
    __tablename__ = "business_coverages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    business_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    business_product_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    shop_id: Mapped[str | None] = mapped_column(String(128), index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), index=True)
    variant_id: Mapped[str | None] = mapped_column(ForeignKey("variants.id", ondelete="RESTRICT"))
    submission_id: Mapped[str | None] = mapped_column(
        ForeignKey("submissions.id", ondelete="RESTRICT"), index=True
    )
    state: Mapped[CoverageState] = enum_column(CoverageState)
    exposure_preference: Mapped[ExposurePreference] = enum_column(
        ExposurePreference, default=ExposurePreference.WIDER
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    location_projection: Mapped[dict[str, Any]] = mapped_column(JSON_VALUE, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    first_linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "variant_id IS NOT NULL OR submission_id IS NOT NULL",
            name="ck_coverage_variant_or_submission",
        ),
        Index(
            "uq_coverage_active_business_product",
            "business_id",
            "business_product_ref",
            unique=True,
            postgresql_where=active.is_(True),
            sqlite_where=active.is_(True),
        ),
    )


class PublicationSnapshot(Base):
    __tablename__ = "publication_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    version: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    state: Mapped[SnapshotState] = enum_column(SnapshotState, default=SnapshotState.CREATED)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("api_clients.client_id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    entries: Mapped[list[PublicationEntry]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )


class PublicationEntry(Base):
    __tablename__ = "publication_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("publication_snapshots.id", ondelete="RESTRICT"), index=True
    )
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    variant_id: Mapped[str] = mapped_column(ForeignKey("variants.id", ondelete="RESTRICT"))
    product_version: Mapped[int] = mapped_column(Integer, nullable=False)
    variant_version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_VALUE, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    snapshot: Mapped[PublicationSnapshot] = relationship(back_populates="entries")

    __table_args__ = (UniqueConstraint("snapshot_id", "variant_id", name="uq_snapshot_variant"),)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    event_type: Mapped[str] = mapped_column(String(96), index=True, nullable=False)
    entity_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    actor_client_id: Mapped[str] = mapped_column(ForeignKey("api_clients.client_id", ondelete="RESTRICT"))
    request_id: Mapped[str | None] = mapped_column(String(128), index=True)
    old_value: Mapped[Any | None] = mapped_column(JSON_VALUE)
    new_value: Mapped[Any | None] = mapped_column(JSON_VALUE)
    rationale: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


def _protect_snapshot_update(_mapper: Any, _connection: Any, target: PublicationSnapshot) -> None:
    state = inspect(target)
    old_states = state.attrs.state.history.deleted
    was_released = any(
        old_state in (SnapshotState.PUBLISHED, SnapshotState.SUPERSEDED, SnapshotState.WITHDRAWN)
        for old_state in old_states
    ) or target.state in (SnapshotState.SUPERSEDED, SnapshotState.WITHDRAWN)
    if not was_released:
        return
    changed = {attribute.key for attribute in state.attrs if attribute.history.has_changes()}
    if not changed.issubset({"state"}):
        raise ValueError("released snapshot content and metadata are immutable")
    if target.state not in (SnapshotState.SUPERSEDED, SnapshotState.WITHDRAWN):
        raise ValueError("released snapshot state cannot return to a mutable state")


def _protect_snapshot_delete(_mapper: Any, _connection: Any, target: PublicationSnapshot) -> None:
    if target.state in (
        SnapshotState.PUBLISHED,
        SnapshotState.SUPERSEDED,
        SnapshotState.WITHDRAWN,
    ):
        raise ValueError("released snapshots cannot be deleted")


def _protect_entry_mutation(_mapper: Any, connection: Any, target: PublicationEntry) -> None:
    state = connection.execute(
        PublicationSnapshot.__table__.select()
        .with_only_columns(PublicationSnapshot.state)
        .where(PublicationSnapshot.id == target.snapshot_id)
    ).scalar_one_or_none()
    if state in (SnapshotState.PUBLISHED, SnapshotState.SUPERSEDED, SnapshotState.WITHDRAWN):
        raise ValueError("released snapshot entries are immutable")


event.listen(PublicationSnapshot, "before_update", _protect_snapshot_update)
event.listen(PublicationSnapshot, "before_delete", _protect_snapshot_delete)
event.listen(PublicationEntry, "before_update", _protect_entry_mutation)
event.listen(PublicationEntry, "before_delete", _protect_entry_mutation)
