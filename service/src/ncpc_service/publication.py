from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from .audit import record_audit
from .auth import Principal
from .database import next_public_id
from .enums import (
    AliasState,
    ApprovalState,
    BarcodeState,
    CoverageState,
    LifecycleState,
    SnapshotState,
    SubmissionState,
)
from .errors import ConflictError
from .models import (
    Alias,
    BarcodeClaim,
    BusinessCoverage,
    Product,
    PublicationEntry,
    PublicationSnapshot,
    Submission,
    Variant,
)
from .public_projection import project_public_identity_payload
from .schemas import PublicationDto


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class PublicationService:
    def __init__(self, session: Session):
        self.session = session

    def publish(
        self,
        principal: Principal,
        *,
        requested_version: str | None = None,
        rationale: str = "Administrator requested publication.",
        request_id: str | None = None,
        variant_ids: set[str] | None = None,
    ) -> PublicationDto:
        principal.require_scope("publications:write")
        items = self._build_items(variant_ids)
        if not items:
            raise ConflictError("there are no approved active variants to publish")
        if variant_ids is not None and len(items) != len(variant_ids):
            raise ConflictError("publication batch contains a non-approved or inactive variant")
        content_hash = sha256_json(items)
        existing = self.session.scalar(
            select(PublicationSnapshot).where(PublicationSnapshot.content_hash == content_hash)
        )
        if existing is not None:
            return self._dto(existing)

        now = datetime.now(UTC)
        public_id = next_public_id(self.session, "REL")
        version = requested_version or f"NCPC-{now:%Y%m%d-%H%M%S}-{public_id.rsplit('-', 1)[-1]}"
        if self.session.scalar(select(PublicationSnapshot.id).where(PublicationSnapshot.version == version)):
            raise ConflictError("publication version already exists")

        current = self.session.scalar(
            select(PublicationSnapshot)
            .where(PublicationSnapshot.state == SnapshotState.PUBLISHED)
            .order_by(desc(PublicationSnapshot.published_at))
            .limit(1)
        )
        if current is not None:
            current.state = SnapshotState.SUPERSEDED

        snapshot = PublicationSnapshot(
            public_id=public_id,
            version=version,
            state=SnapshotState.CREATED,
            content_hash=content_hash,
            item_count=len(items),
            created_by=principal.client_id,
            created_at=now,
        )
        self.session.add(snapshot)
        self.session.flush()
        variant_ids: set[str] = set()
        for item in items:
            product = self.session.scalar(select(Product).where(Product.public_id == item["ncpc_product_id"]))
            variant = self.session.scalar(select(Variant).where(Variant.public_id == item["ncpc_variant_id"]))
            assert product is not None and variant is not None
            variant_ids.add(variant.id)
            self.session.add(
                PublicationEntry(
                    snapshot_id=snapshot.id,
                    product_id=product.id,
                    variant_id=variant.id,
                    product_version=product.version,
                    variant_version=variant.version,
                    payload=item,
                    content_hash=sha256_json(item),
                )
            )
        self.session.flush()
        snapshot.state = SnapshotState.PUBLISHED
        snapshot.published_at = now
        self._promote_submissions_and_coverage(variant_ids, now)
        record_audit(
            self.session,
            event_type="PUBLICATION_CREATED",
            entity_kind="PUBLICATION",
            entity_id=snapshot.public_id,
            actor_client_id=principal.client_id,
            request_id=request_id,
            new_value={
                "version": snapshot.version,
                "content_hash": snapshot.content_hash,
                "item_count": snapshot.item_count,
            },
        )
        self.session.flush()
        return self._dto(snapshot)

    def list_publications(self, principal: Principal, limit: int = 50) -> list[PublicationDto]:
        principal.require_scope("publications:read")
        rows = self.session.scalars(
            select(PublicationSnapshot)
            .order_by(desc(PublicationSnapshot.created_at))
            .limit(min(max(limit, 1), 100))
        ).all()
        return [self._dto(row) for row in rows]

    def publish_identities(
        self,
        principal: Principal,
        *,
        variant_ids: set[str],
        product_ids: set[str],
        requested_version: str | None,
        rationale: str,
        request_id: str | None = None,
    ) -> PublicationDto:
        """Publish an explicitly approved seed subset without broadening release scope."""
        if product_ids:
            raise ConflictError("product-only publication requires the pending schema migration")
        if not variant_ids:
            raise ConflictError("publication batch contains no identities")
        return self.publish(
            principal,
            requested_version=requested_version,
            rationale=rationale,
            request_id=request_id,
            variant_ids=variant_ids,
        )

    def _build_items(self, only_variant_ids: set[str] | None = None) -> list[dict[str, Any]]:
        query = (
            select(Variant)
            .join(Product, Variant.product_id == Product.id)
            .where(
                Variant.lifecycle == LifecycleState.ACTIVE,
                Variant.approval_state == ApprovalState.APPROVED,
                Product.lifecycle == LifecycleState.ACTIVE,
                Product.approval_state == ApprovalState.APPROVED,
            )
            .order_by(Product.public_id, Variant.public_id)
        )
        if only_variant_ids is not None:
            query = query.where(Variant.public_id.in_(only_variant_ids))
        variants = self.session.scalars(query).all()
        items: list[dict[str, Any]] = []
        for variant in variants:
            product = variant.product
            identifiers = list(
                self.session.scalars(
                    select(BarcodeClaim.original_value)
                    .where(
                        BarcodeClaim.variant_id == variant.id,
                        BarcodeClaim.state == BarcodeState.VERIFIED_ACTIVE,
                        BarcodeClaim.active.is_(True),
                    )
                    .order_by(BarcodeClaim.original_value)
                )
            )
            aliases = list(
                self.session.scalars(
                    select(Alias.display_text)
                    .where(
                        ((Alias.variant_id == variant.id) | (Alias.product_id == product.id)),
                        Alias.state == AliasState.APPROVED,
                    )
                    .order_by(Alias.display_text)
                )
            )
            items.append(
                project_public_identity_payload(
                    {
                        "ncpc_product_id": product.public_id,
                        "ncpc_variant_id": variant.public_id,
                        "canonical_name": product.canonical_name,
                        "variant_name": variant.canonical_name,
                        "brand": product.brand.canonical_name if product.brand else None,
                        "category": product.category.canonical_name if product.category else None,
                        "pack_definition": variant.pack_definition,
                        "attributes": variant.attributes,
                        "identifiers": identifiers,
                        "aliases": aliases,
                    }
                )
            )
        return items

    def _promote_submissions_and_coverage(
        self, published_variant_ids: set[str], published_at: datetime
    ) -> None:
        submissions = self.session.scalars(
            select(Submission).where(
                Submission.state == SubmissionState.APPROVED,
                Submission.target_variant_id.in_(published_variant_ids),
            )
        ).all()
        for submission in submissions:
            submission.state = SubmissionState.PUBLISHED
            submission.published_at = published_at
        coverages = self.session.scalars(
            select(BusinessCoverage).where(
                BusinessCoverage.active.is_(True),
                BusinessCoverage.variant_id.in_(published_variant_ids),
                BusinessCoverage.state.in_(
                    [CoverageState.SUBMITTED_PENDING, CoverageState.STALE, CoverageState.REMAPPED]
                ),
            )
        ).all()
        for coverage in coverages:
            coverage.state = CoverageState.LINKED_APPROVED
            coverage.last_confirmed_at = published_at

    @staticmethod
    def _dto(snapshot: PublicationSnapshot) -> PublicationDto:
        return PublicationDto(
            snapshot_id=snapshot.public_id,
            version=snapshot.version,
            state=snapshot.state.value,
            content_hash=snapshot.content_hash,
            item_count=snapshot.item_count,
            created_at=snapshot.created_at,
            published_at=snapshot.published_at,
        )
