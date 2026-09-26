"""Owner-authorized, identity-only initial catalogue seeding.

This service is deliberately separate from TradeFlow submissions: a physical
catalogue observation is provenance, not a business coverage or local SKU.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .audit import record_audit
from .auth import Principal
from .database import next_public_id
from .enums import AliasState, ApprovalState, BarcodeState, LifecycleState, ReviewOutcome, ReviewState, SnapshotState, SubmissionState, SubmissionType
from .errors import ConflictError
from .models import Alias, BarcodeClaim, Brand, BrandOrganizationRelationship, CatalogueEvidence, EvidenceSource, Organization, Product, PublicationEntry, PublicationSnapshot, ReviewCase, ReviewDecision, SeedBatch, SeedBatchItem, Submission, Variant
from .normalization import normalize_barcode, normalize_text
from .publication import PublicationService, sha256_json


DECISION_TYPE = "INITIAL_OWNER_AUTHORIZED_PUBLICATION"


@dataclass(frozen=True)
class SeedResult:
    batch_id: str
    publication_id: str | None
    published_variants: int
    published_product_families: int
    held_conflicts: list[dict[str, str]]


class InitialSeedService:
    def __init__(self, session: Session):
        self.session = session

    def apply(self, manifest: dict[str, Any], principal: Principal, *, request_id: str | None = None) -> SeedResult:
        principal.require_scope("publications:write")
        if manifest.get("schema_version") != "ncpc-initial-seed-manifest-v1":
            raise ConflictError("unsupported seed manifest schema")
        if manifest.get("decision_type") != DECISION_TYPE or not manifest.get("actor_label"):
            raise ConflictError("seed manifest lacks explicit owner-authorized decision metadata")
        supplied_hash = str(manifest.get("manifest_hash", ""))
        hash_fields = {
            "schema_version", "source_fingerprint", "decision_type", "actor_label",
            "sources", "candidates", "product_only_candidates", "held_for_review", "summary",
        }
        legacy_hash_input = {
            key: value for key, value in manifest.items() if key in hash_fields
        }
        # The original seed manifest format did not bind its rationale. The
        # official-source expansion builder does bind it. Accept both known
        # canonical formats for backward-compatible replay, but never accept a
        # hash over an arbitrary subset of the manifest.
        rationale_bound_hash_input = {
            **legacy_hash_input,
            **({"rationale": manifest["rationale"]} if "rationale" in manifest else {}),
        }
        if supplied_hash not in {
            sha256_json(legacy_hash_input),
            sha256_json(rationale_bound_hash_input),
        }:
            raise ConflictError("seed manifest hash does not match its content")
        existing = self.session.scalar(select(SeedBatch).where(SeedBatch.manifest_hash == supplied_hash))
        if existing is not None:
            items = self.session.scalars(select(SeedBatchItem).where(SeedBatchItem.batch_id == existing.id)).all()
            return SeedResult(
                existing.public_id,
                None,
                sum(item.variant_id is not None for item in items),
                sum(item.variant_id is None for item in items),
                [],
            )

        sources = self._sources(manifest["sources"])
        batch = SeedBatch(
            public_id=next_public_id(self.session, "SEED"), manifest_hash=supplied_hash,
            decision_type=DECISION_TYPE, actor_label=str(manifest["actor_label"]),
            rationale=str(
                manifest.get("rationale")
                or "Identity established by owner-supplied physical evidence under initial NCPC publication rules."
            ),
            created_by=principal.client_id,
        )
        self.session.add(batch); self.session.flush()
        applied: set[str] = set()
        product_only_applied: set[str] = set()
        held: list[dict[str, str]] = []
        for held_row in manifest.get("held_for_review", []):
            self._hold_manifest_row(held_row, principal, request_id)
            held.append({"source_ref": str(held_row["source_ref"]), "reason": str(held_row["reason"])})
        for candidate in manifest.get("candidates", []):
            conflict = self._preflight_conflict(candidate)
            if conflict is not None:
                self._hold_review(candidate, conflict, principal, request_id)
                held.append({"source_ref": str(candidate["source_ref"]), "reason": conflict})
                continue
            product, variant = self._identity(candidate)
            if variant.public_id in applied:
                self._hold_review(candidate, "duplicate manifest row resolves to the same product/variant", principal, request_id, product, variant)
                held.append({
                    "source_ref": str(candidate["source_ref"]),
                    "reason": "duplicate manifest row resolves to the same product/variant",
                })
                continue
            review = self._owner_decision(candidate, product, variant, principal, request_id)
            self._barcode(candidate, variant)
            self._aliases(candidate, product, variant)
            self._evidence(candidate, sources, product, variant)
            self._organization_relationship(candidate, product, sources)
            # A VAR and its decision have immutable first-seed lineage. A later
            # manifest may enrich aliases/evidence but must not re-parent either
            # record to a second batch.
            if self.session.scalar(select(SeedBatchItem).where(SeedBatchItem.variant_id == variant.id)) is None:
                self.session.add(SeedBatchItem(batch_id=batch.id, product_id=product.id, variant_id=variant.id, review_case_id=review.id))
            applied.add(variant.public_id)
        for candidate in manifest.get("product_only_candidates", []):
            lifecycle_conflict = self._product_lifecycle_conflict(candidate)
            if lifecycle_conflict is not None:
                self._hold_manifest_row({
                    "source_ref": candidate["source_ref"],
                    "classification": "CLASS_B_PRODUCT_FAMILY_RECONCILIATION",
                    "reason": lifecycle_conflict,
                }, principal, request_id)
                held.append({"source_ref": str(candidate["source_ref"]), "reason": lifecycle_conflict})
                continue
            product = self._product_identity(candidate)
            if product.public_id in product_only_applied:
                self._hold_manifest_row({"source_ref": candidate["source_ref"], "classification": "CLASS_B_PRODUCT_FAMILY_RECONCILIATION", "reason": "duplicate manifest row resolves to the same product family"}, principal, request_id)
                held.append({"source_ref": str(candidate["source_ref"]), "reason": "duplicate manifest row resolves to the same product family"})
                continue
            if self.session.scalar(select(Variant.id).where(Variant.product_id == product.id)) is not None:
                self._hold_manifest_row({"source_ref": candidate["source_ref"], "classification": "CLASS_B_PRODUCT_FAMILY_RECONCILIATION", "reason": "product family already has variants and requires reconciliation"}, principal, request_id)
                held.append({"source_ref": str(candidate["source_ref"]), "reason": "product family already has variants and requires reconciliation"})
                continue
            review = self._owner_decision(candidate, product, None, principal, request_id)
            self._aliases(candidate, product, None)
            self._evidence(candidate, sources, product, None)
            self._organization_relationship(candidate, product, sources)
            if self.session.scalar(select(SeedBatchItem).where(SeedBatchItem.product_id == product.id, SeedBatchItem.variant_id.is_(None))) is None:
                self.session.add(SeedBatchItem(batch_id=batch.id, product_id=product.id, variant_id=None, review_case_id=review.id))
            product_only_applied.add(product.public_id)
        self.session.flush()
        publication = None
        if applied or product_only_applied:
            current = self.session.scalar(select(PublicationSnapshot).where(PublicationSnapshot.state == SnapshotState.PUBLISHED))
            retained_variants: set[str] = set()
            retained_products: set[str] = set()
            if current is not None:
                for entry in self.session.scalars(select(PublicationEntry).where(PublicationEntry.snapshot_id == current.id)):
                    if entry.variant_id is None:
                        retained_products.add(entry.product_id)
                    else:
                        retained_variants.add(entry.variant_id)
            retained_variant_public_ids = set(self.session.scalars(select(Variant.public_id).where(Variant.id.in_(retained_variants))))
            new_variant_product_ids = set(
                self.session.scalars(select(Variant.product_id).where(Variant.public_id.in_(applied)))
            )
            retained_product_public_ids = set(
                self.session.scalars(
                    select(Product.public_id).where(
                        Product.id.in_(retained_products - new_variant_product_ids)
                    )
                )
            )
            publication = PublicationService(self.session).publish_identities(
                principal,
                variant_ids=applied | retained_variant_public_ids,
                product_ids=product_only_applied | retained_product_public_ids,
                requested_version=None,
                rationale=f"{DECISION_TYPE} seed batch {batch.public_id}", request_id=request_id,
            )
            snapshot = self.session.scalar(
                select(PublicationSnapshot).where(PublicationSnapshot.public_id == publication.snapshot_id)
            )
            assert snapshot is not None
            batch.publication_id = snapshot.id
        record_audit(self.session, event_type="INITIAL_OWNER_AUTHORIZED_SEED_APPLIED", entity_kind="SEED_BATCH", entity_id=batch.public_id, actor_client_id=principal.client_id, request_id=request_id, new_value={"manifest_hash": supplied_hash, "published_variants": len(applied), "held_conflicts": held}, rationale=batch.rationale)
        self.session.flush()
        return SeedResult(
            batch.public_id,
            publication.snapshot_id if publication else None,
            len(applied),
            len(product_only_applied),
            held,
        )

    def _sources(self, rows: list[dict[str, Any]]) -> dict[str, EvidenceSource]:
        result: dict[str, EvidenceSource] = {}
        for row in rows:
            key = str(row["source_key"])
            source = self.session.scalar(select(EvidenceSource).where(EvidenceSource.source_key == key))
            if source is None:
                source = EvidenceSource(source_key=key, title=str(row["title"]), source_url=row.get("source_url"), source_type=str(row["source_type"]), authority=str(row["authority"]), accessed_at=datetime.fromisoformat(str(row["accessed_at"])), notes=row.get("notes"))
                self.session.add(source); self.session.flush()
            result[key] = source
        return result

    def _identity(self, candidate: dict[str, Any]) -> tuple[Product, Variant]:
        product_row, variant_row = candidate["product"], candidate["variant"]
        product = self._product_identity(candidate)
        matched_variant_id = candidate.get("match_existing_variant_id")
        if matched_variant_id:
            variant = self.session.scalar(
                select(Variant).where(Variant.public_id == str(matched_variant_id))
            )
            if variant is None or variant.product_id != product.id:
                raise ConflictError("matched existing variant is not part of the resolved product")
            if variant.lifecycle != LifecycleState.ACTIVE:
                raise ConflictError("matched existing variant has a non-active lifecycle")
            if variant.approval_state == ApprovalState.DRAFT:
                variant.approval_state = ApprovalState.APPROVED
            return product, variant
        variant = self.session.scalar(select(Variant).where(Variant.product_id == product.id, Variant.normalized_name == normalize_text(variant_row["canonical_name"])))
        if variant is None:
            variant = Variant(public_id=next_public_id(self.session, "VAR"), product_id=product.id, canonical_name=variant_row["canonical_name"], normalized_name=normalize_text(variant_row["canonical_name"]), pack_definition=variant_row.get("pack_definition", {}), attributes=variant_row.get("attributes", {}), lifecycle=LifecycleState.ACTIVE, approval_state=ApprovalState.APPROVED, provenance={"seed_manifest_ref": candidate["source_ref"], "identity_only": True})
            self.session.add(variant); self.session.flush()
        elif variant.approval_state == ApprovalState.DRAFT:
            # The manifest is explicit approval authority for this exact
            # legacy DRAFT identity. Barcode preflight still holds any
            # incompatible verified barcode rather than changing it.
            variant.lifecycle = LifecycleState.ACTIVE
            variant.approval_state = ApprovalState.APPROVED
        return product, variant

    def _product_identity(self, candidate: dict[str, Any]) -> Product:
        product_row = candidate["product"]
        brand = None
        if product_row.get("brand"):
            brand = self.session.scalar(select(Brand).where(Brand.normalized_name == normalize_text(str(product_row["brand"]))))
            if brand is None:
                brand = Brand(canonical_name=str(product_row["brand"]), normalized_name=normalize_text(str(product_row["brand"])), lifecycle=LifecycleState.ACTIVE)
                self.session.add(brand); self.session.flush()
        product = self.session.scalar(select(Product).where(Product.normalized_name == normalize_text(product_row["canonical_name"])))
        if product is None:
            product = Product(public_id=next_public_id(self.session, "PRD"), canonical_name=product_row["canonical_name"], normalized_name=normalize_text(product_row["canonical_name"]), brand_id=brand.id if brand else None, lifecycle=LifecycleState.ACTIVE, approval_state=ApprovalState.APPROVED, provenance={"seed_manifest_ref": candidate["source_ref"], "identity_only": True})
            self.session.add(product); self.session.flush()
        elif product.approval_state == ApprovalState.DRAFT:
            # Do not create a second product for an exact legacy identity that
            # predates controlled seed approval; promote only this exact DRAFT
            # manifest match to publishable state.
            product.lifecycle = LifecycleState.ACTIVE
            product.approval_state = ApprovalState.APPROVED
            if brand is not None and product.brand_id is None:
                product.brand_id = brand.id
        elif brand is not None and product.brand_id is None:
            # An exact active identity may gain an evidence-backed brand only
            # when it has no existing brand. A conflicting brand is held as-is.
            product.brand_id = brand.id
        return product

    def _aliases(self, candidate: dict[str, Any], product: Product, variant: Variant | None) -> None:
        for row in candidate.get("aliases", []):
            display = str(row["display_text"]).strip()
            if not display:
                continue
            normalized = normalize_text(display)
            existing = self.session.scalar(select(Alias).where(Alias.normalized_text == normalized, Alias.product_id == product.id, Alias.variant_id.is_(None)))
            if existing is None:
                self.session.add(Alias(display_text=display, normalized_text=normalized, product_id=product.id, variant_id=None, alias_kind=str(row.get("alias_kind", "COMMON")), state=AliasState.APPROVED, source="owner_authorized_initial_seed", provenance={"seed_manifest_ref": candidate["source_ref"], "evidence_source_key": row.get("source_key")}))

    def _organization_relationship(
        self, candidate: dict[str, Any], product: Product, sources: dict[str, EvidenceSource]
    ) -> None:
        """Persist only an explicitly manifested, source-backed brand relationship."""
        relationship = candidate.get("organization_relationship")
        if not relationship or product.brand is None:
            return
        organization_name = str(relationship["organization_name"])
        organization = self.session.scalar(
            select(Organization).where(Organization.normalized_name == normalize_text(organization_name))
        )
        if organization is None:
            organization = Organization(
                canonical_name=organization_name,
                normalized_name=normalize_text(organization_name),
                lifecycle=LifecycleState.ACTIVE,
            )
            self.session.add(organization)
            self.session.flush()
        source_key = str(relationship["source_key"])
        source = sources[source_key]
        existing = self.session.scalar(
            select(BrandOrganizationRelationship).where(
                BrandOrganizationRelationship.brand_id == product.brand.id,
                BrandOrganizationRelationship.organization_id == organization.id,
                BrandOrganizationRelationship.relationship_type == str(relationship["relationship_type"]),
            )
        )
        if existing is None:
            self.session.add(
                BrandOrganizationRelationship(
                    brand_id=product.brand.id,
                    organization_id=organization.id,
                    relationship_type=str(relationship["relationship_type"]),
                    evidence_source_id=source.id,
                    verification_status="VERIFIED",
                )
            )

    def _preflight_conflict(self, candidate: dict[str, Any]) -> str | None:
        barcode = candidate["variant"].get("barcode")
        product_row, variant_row = candidate["product"], candidate["variant"]
        product = self.session.scalar(select(Product).where(Product.normalized_name == normalize_text(product_row["canonical_name"])))
        variant = None if product is None else self.session.scalar(
            select(Variant).where(
                Variant.product_id == product.id,
                Variant.normalized_name == normalize_text(variant_row["canonical_name"]),
            )
        )
        if product is not None and product.lifecycle != LifecycleState.ACTIVE:
            return "existing product has a non-active lifecycle and requires reconciliation"
        if variant is not None and variant.lifecycle != LifecycleState.ACTIVE:
            return "existing variant has a non-active lifecycle and requires reconciliation"
        if not barcode:
            return None
        owner = self.session.scalar(select(BarcodeClaim).where(BarcodeClaim.normalized_value == normalize_barcode(str(barcode)), BarcodeClaim.state == BarcodeState.VERIFIED_ACTIVE, BarcodeClaim.active.is_(True)))
        if owner is not None and (variant is None or owner.variant_id != variant.id):
            return "verified barcode is already attached to another variant"
        if variant is not None:
            existing = self.session.scalars(select(BarcodeClaim).where(
                BarcodeClaim.variant_id == variant.id,
                BarcodeClaim.state == BarcodeState.VERIFIED_ACTIVE,
                BarcodeClaim.active.is_(True),
            )).all()
            if any(claim.normalized_value != normalize_barcode(str(barcode)) for claim in existing):
                return "existing variant has a different verified barcode and requires reconciliation"
        return None

    def _product_lifecycle_conflict(self, candidate: dict[str, Any]) -> str | None:
        """Do not revive a retired, merged, or deprecated product as Class B."""
        product = self.session.scalar(
            select(Product).where(
                Product.normalized_name == normalize_text(candidate["product"]["canonical_name"])
            )
        )
        if product is not None and product.lifecycle != LifecycleState.ACTIVE:
            return "existing product has a non-active lifecycle and requires reconciliation"
        return None

    def _barcode(self, candidate: dict[str, Any], variant: Variant) -> None:
        barcode = candidate["variant"].get("barcode")
        if barcode and self.session.scalar(select(BarcodeClaim).where(BarcodeClaim.variant_id == variant.id, BarcodeClaim.normalized_value == normalize_barcode(str(barcode)))) is None:
            self.session.add(BarcodeClaim(variant_id=variant.id, original_value=str(barcode), normalized_value=normalize_barcode(str(barcode)), symbology=None, state=BarcodeState.VERIFIED_ACTIVE, source="owner_authorized_initial_seed", source_ref=str(candidate["source_ref"]), provenance={"identity_only": True}, active=True))

    def _owner_decision(self, candidate: dict[str, Any], product: Product, variant: Variant | None, principal: Principal, request_id: str | None) -> ReviewCase:
        idempotency_key = f"seed:{candidate['source_ref']}:{variant.public_id if variant else product.public_id}"
        existing = self.session.scalar(select(Submission).where(Submission.submitter_client_id == principal.client_id, Submission.idempotency_key == idempotency_key))
        if existing is not None:
            review = self.session.scalar(select(ReviewCase).where(ReviewCase.submission_id == existing.id))
            if review is None:
                raise ConflictError("existing seed submission has no review case")
            return review
        submission = Submission(public_id=next_public_id(self.session, "SUB"), submission_type=SubmissionType.NEW_PRODUCT, state=SubmissionState.APPROVED, business_id=None, business_product_ref=None, target_product_id=product.id, target_variant_id=variant.id if variant else None, source="owner_authorized_initial_seed", submitter_client_id=principal.client_id, idempotency_key=idempotency_key)
        self.session.add(submission); self.session.flush()
        review = ReviewCase(public_id=next_public_id(self.session, "REV"), submission_id=submission.id, reason="INITIAL_OWNER_AUTHORIZED_SEED", state=ReviewState.DECIDED)
        self.session.add(review); self.session.flush()
        self.session.add(ReviewDecision(review_case_id=review.id, reviewer_client_id=principal.client_id, outcome=ReviewOutcome.INITIAL_OWNER_AUTHORIZED_PUBLICATION, rationale="Owner-authorized initial seed; evidence is retained per claim.", evidence={"source_ref": candidate["source_ref"], "decision_type": DECISION_TYPE}, decision_data={"actor_label": "owner-authorized import", "not_human_review": True}))
        record_audit(self.session, event_type="INITIAL_OWNER_AUTHORIZED_PUBLICATION_DECIDED", entity_kind="REVIEW", entity_id=review.public_id, actor_client_id=principal.client_id, request_id=request_id, new_value={"source_ref": candidate["source_ref"], "decision_type": DECISION_TYPE, "product_id": product.public_id, "variant_id": variant.public_id if variant else None}, rationale="Owner-authorized initial seed; not a human reviewer decision.")
        return review

    def _hold_review(self, candidate: dict[str, Any], reason: str, principal: Principal, request_id: str | None, product: Product | None = None, variant: Variant | None = None) -> None:
        idempotency_key = f"seed-hold:{candidate['source_ref']}:{candidate['variant'].get('barcode') or 'no-barcode'}"
        if self.session.scalar(select(Submission).where(Submission.submitter_client_id == principal.client_id, Submission.idempotency_key == idempotency_key)) is not None:
            return
        submission = Submission(public_id=next_public_id(self.session, "SUB"), submission_type=SubmissionType.POSSIBLE_DUPLICATE, state=SubmissionState.PENDING_REVIEW, business_id=None, business_product_ref=None, target_product_id=product.id if product else None, target_variant_id=variant.id if variant else None, source="owner_authorized_initial_seed", submitter_client_id=principal.client_id, idempotency_key=idempotency_key)
        self.session.add(submission); self.session.flush()
        review = ReviewCase(public_id=next_public_id(self.session, "REV"), submission_id=submission.id, reason="INITIAL_SEED_CONFLICT", state=ReviewState.OPEN)
        self.session.add(review)
        record_audit(self.session, event_type="INITIAL_SEED_CONFLICT_HELD", entity_kind="REVIEW", entity_id=review.public_id, actor_client_id=principal.client_id, request_id=request_id, new_value={"source_ref": candidate["source_ref"], "reason": reason}, rationale="Seed conflict held for normal manual review.")

    def _hold_manifest_row(self, row: dict[str, Any], principal: Principal, request_id: str | None) -> None:
        """Persist every non-candidate workbook row as a normal, open review case."""
        idempotency_key = f"seed-manifest-hold:{row['source_ref']}"
        if self.session.scalar(select(Submission).where(Submission.submitter_client_id == principal.client_id, Submission.idempotency_key == idempotency_key)) is not None:
            return
        submission = Submission(
            public_id=next_public_id(self.session, "SUB"),
            submission_type=SubmissionType.POSSIBLE_DUPLICATE,
            state=SubmissionState.PENDING_REVIEW,
            business_id=None,
            business_product_ref=None,
            source="owner_authorized_initial_seed",
            submitter_client_id=principal.client_id,
            idempotency_key=idempotency_key,
        )
        self.session.add(submission); self.session.flush()
        review = ReviewCase(
            public_id=next_public_id(self.session, "REV"),
            submission_id=submission.id,
            reason=str(row["classification"]),
            state=ReviewState.OPEN,
        )
        self.session.add(review)
        record_audit(
            self.session,
            event_type="INITIAL_SEED_MANIFEST_HOLD_CREATED",
            entity_kind="REVIEW",
            entity_id=review.public_id,
            actor_client_id=principal.client_id,
            request_id=request_id,
            new_value={"source_ref": row["source_ref"], "reason": row["reason"], "classification": row["classification"]},
            rationale="Workbook row was intentionally excluded from initial publication and held for normal review.",
        )

    def _evidence(self, candidate: dict[str, Any], sources: dict[str, EvidenceSource], product: Product, variant: Variant | None) -> None:
        for item in candidate.get("evidence", []):
            source = sources[str(item["source_key"])]
            existing = self.session.scalar(select(CatalogueEvidence).where(CatalogueEvidence.source_id == source.id, CatalogueEvidence.product_id == product.id, CatalogueEvidence.variant_id == (variant.id if variant else None), CatalogueEvidence.claim_type == str(item["claim_type"]), CatalogueEvidence.claim_value == str(item["claim_value"])))
            if existing is None:
                self.session.add(CatalogueEvidence(source_id=source.id, product_id=product.id, variant_id=variant.id if variant else None, claim_type=str(item["claim_type"]), claim_value=str(item["claim_value"]), evidence_tier=str(item["evidence_tier"]), confidence=str(item["confidence"]), verification_status=str(item["verification_status"]), image_reference=item.get("image_reference"), notes=item.get("notes")))
