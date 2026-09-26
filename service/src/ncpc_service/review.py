from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
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
    ReviewOutcome,
    ReviewState,
    SubmissionState,
)
from .errors import InvalidTransitionError, NotFoundError
from .models import (
    Alias,
    BarcodeClaim,
    Brand,
    BusinessCoverage,
    Category,
    Product,
    PublicationEntry,
    PublicationSnapshot,
    ReviewCase,
    ReviewDecision,
    Submission,
    Variant,
)
from .normalization import normalize_barcode, normalize_text
from .schemas import ReviewDecisionRequest, ReviewDto, SubmissionStatusDto
from .submissions import SubmissionService


class ReviewService:
    def __init__(self, session: Session):
        self.session = session

    def list_open(self, principal: Principal, limit: int = 100) -> list[ReviewDto]:
        principal.require_scope("reviews:read")
        cases = self.session.scalars(
            select(ReviewCase)
            .where(
                ReviewCase.state.in_(
                    [ReviewState.OPEN, ReviewState.IN_REVIEW, ReviewState.NEEDS_MORE_INFORMATION]
                )
            )
            .order_by(ReviewCase.created_at)
            .limit(min(max(limit, 1), 200))
        ).all()
        return [self._dto(case) for case in cases]

    def get(self, review_id: str, principal: Principal) -> ReviewDto:
        principal.require_scope("reviews:read")
        review = self.session.scalar(select(ReviewCase).where(ReviewCase.public_id == review_id))
        if review is None:
            raise NotFoundError("review case not found")
        return self._dto(review)

    def decide(
        self,
        review_id: str,
        request: ReviewDecisionRequest,
        principal: Principal,
        *,
        request_id: str | None = None,
    ) -> SubmissionStatusDto:
        principal.require_scope("reviews:decide")
        review = self.session.scalar(
            select(ReviewCase).where(ReviewCase.public_id == review_id).with_for_update()
        )
        if review is None:
            raise NotFoundError("review case not found")
        if review.state in (ReviewState.DECIDED, ReviewState.CLOSED):
            raise InvalidTransitionError("review case is already decided")
        submission = review.submission
        if submission.state not in (
            SubmissionState.PENDING_REVIEW,
            SubmissionState.NEEDS_CHANGES,
        ):
            raise InvalidTransitionError("submission is not reviewable")

        decision = ReviewDecision(
            review_case_id=review.id,
            reviewer_client_id=principal.client_id,
            outcome=request.outcome,
            rationale=request.rationale,
            evidence=request.evidence,
            decision_data=request.model_dump(mode="json", exclude={"rationale", "evidence"}),
        )
        self.session.add(decision)

        if request.outcome == ReviewOutcome.NEEDS_MORE_INFORMATION:
            submission.state = SubmissionState.NEEDS_CHANGES
            review.state = ReviewState.NEEDS_MORE_INFORMATION
            self._update_new_coverage(submission, CoverageState.NEEDS_MORE_INFORMATION)
        elif request.outcome == ReviewOutcome.REJECT:
            submission.state = SubmissionState.REJECTED
            submission.decided_at = datetime.now(UTC)
            review.state = ReviewState.DECIDED
            self._update_new_coverage(submission, CoverageState.REJECTED)
        elif request.outcome == ReviewOutcome.WITHDRAW:
            submission.state = SubmissionState.WITHDRAWN
            submission.decided_at = datetime.now(UTC)
            review.state = ReviewState.DECIDED
            self._update_new_coverage(submission, CoverageState.WITHDRAWN)
        elif request.outcome == ReviewOutcome.MATCH_EXISTING:
            self._match_existing(submission, request)
            review.state = ReviewState.DECIDED
        elif request.outcome == ReviewOutcome.APPROVE_NEW:
            self._approve_new(submission, request, principal)
            review.state = ReviewState.DECIDED
        elif request.outcome == ReviewOutcome.APPROVE_CORRECTION:
            self._approve_correction(submission, principal)
            review.state = ReviewState.DECIDED
        else:  # pragma: no cover - guarded by the enum
            raise InvalidTransitionError("unsupported review outcome")

        self.session.flush()
        record_audit(
            self.session,
            event_type="REVIEW_DECIDED",
            entity_kind="REVIEW",
            entity_id=review.public_id,
            actor_client_id=principal.client_id,
            request_id=request_id,
            new_value={"outcome": request.outcome.value, "submission_state": submission.state.value},
            rationale=request.rationale,
        )
        return SubmissionService(self.session).status(submission, principal)

    def _approve_new(
        self, submission: Submission, request: ReviewDecisionRequest, principal: Principal
    ) -> None:
        changes = self._changes(submission)
        product_name = request.canonical_name or changes.get("product.canonical_name")
        if not product_name:
            raise InvalidTransitionError("canonical product name is required for approval")
        variant_name = request.variant_name or changes.get("variant.canonical_name") or product_name
        brand_name = request.brand or changes.get("product.brand")
        category_name = request.category or changes.get("product.category")
        brand = self._get_or_create_brand(brand_name) if brand_name else None
        category = self._get_or_create_category(category_name) if category_name else None
        product = Product(
            public_id=next_public_id(self.session, "PRD"),
            canonical_name=product_name,
            normalized_name=normalize_text(product_name),
            brand_id=brand.id if brand else None,
            category_id=category.id if category else None,
            lifecycle=LifecycleState.ACTIVE,
            approval_state=ApprovalState.APPROVED,
            provenance={"submission_id": submission.public_id, "source": submission.source},
        )
        self.session.add(product)
        self.session.flush()
        variant = Variant(
            public_id=next_public_id(self.session, "VAR"),
            product_id=product.id,
            canonical_name=variant_name,
            normalized_name=normalize_text(variant_name),
            pack_definition=request.pack_definition
            if request.pack_definition is not None
            else changes.get("variant.pack_definition", {}),
            attributes=changes.get("variant.attributes", {}),
            lifecycle=LifecycleState.ACTIVE,
            approval_state=ApprovalState.APPROVED,
            provenance={"submission_id": submission.public_id, "source": submission.source},
        )
        self.session.add(variant)
        self.session.flush()
        self._approve_aliases(variant, changes.get("variant.aliases", []), submission)
        self._approve_barcodes(variant, changes.get("variant.barcodes", []), submission)
        submission.target_product_id = product.id
        submission.target_variant_id = variant.id
        submission.state = SubmissionState.APPROVED
        submission.decided_at = datetime.now(UTC)
        self._link_new_coverage(submission, variant, trusted=False)
        record_audit(
            self.session,
            event_type="IDENTITY_CREATED",
            entity_kind="VARIANT",
            entity_id=variant.public_id,
            actor_client_id=principal.client_id,
            new_value={"product_id": product.public_id, "variant_id": variant.public_id},
        )

    def _match_existing(self, submission: Submission, request: ReviewDecisionRequest) -> None:
        if not request.matched_variant_id:
            raise InvalidTransitionError("matched_variant_id is required")
        variant = self.session.scalar(
            select(Variant).where(
                Variant.public_id == request.matched_variant_id,
                Variant.lifecycle == LifecycleState.ACTIVE,
                Variant.approval_state == ApprovalState.APPROVED,
            )
        )
        if variant is None:
            raise NotFoundError("approved active variant not found")
        submission.target_product_id = variant.product_id
        submission.target_variant_id = variant.id
        submission.state = SubmissionState.APPROVED
        submission.decided_at = datetime.now(UTC)
        self._link_new_coverage(submission, variant, trusted=self._is_published(variant.id))

    def _approve_correction(self, submission: Submission, principal: Principal) -> None:
        if not submission.target_variant_id or not submission.target_product_id:
            raise InvalidTransitionError("correction target is missing")
        product = self.session.get(Product, submission.target_product_id)
        variant = self.session.get(Variant, submission.target_variant_id)
        if product is None or variant is None:
            raise NotFoundError("correction target not found")
        changes = self._changes(submission)
        old_value = {
            "product_name": product.canonical_name,
            "variant_name": variant.canonical_name,
            "pack_definition": variant.pack_definition,
        }
        for path, value in changes.items():
            if path == "product.canonical_name":
                product.canonical_name = str(value)
                product.normalized_name = normalize_text(str(value))
                product.version += 1
            elif path == "variant.canonical_name":
                variant.canonical_name = str(value)
                variant.normalized_name = normalize_text(str(value))
                variant.version += 1
            elif path == "variant.pack_definition":
                variant.pack_definition = dict(value)
                variant.version += 1
            elif path == "variant.attributes":
                variant.attributes = dict(value)
                variant.version += 1
            elif path == "product.brand":
                brand = self._get_or_create_brand(str(value))
                product.brand_id = brand.id
                product.version += 1
            elif path == "product.category":
                category = self._get_or_create_category(str(value))
                product.category_id = category.id
                product.version += 1
            elif path == "variant.barcodes":
                self._approve_barcodes(variant, list(value), submission)
            elif path == "variant.aliases":
                self._approve_aliases(variant, list(value), submission)
            else:
                raise InvalidTransitionError(f"unsupported correction path: {path}")
        submission.state = SubmissionState.APPROVED
        submission.decided_at = datetime.now(UTC)
        record_audit(
            self.session,
            event_type="IDENTITY_CORRECTED",
            entity_kind="VARIANT",
            entity_id=variant.public_id,
            actor_client_id=principal.client_id,
            old_value=old_value,
            new_value=changes,
        )

    def _approve_barcodes(
        self, variant: Variant, barcode_items: list[dict[str, Any]], submission: Submission
    ) -> None:
        for item in barcode_items:
            original = str(item["value"])
            normalized = normalize_barcode(original)
            trusted = self.session.scalar(
                select(BarcodeClaim).where(
                    BarcodeClaim.normalized_value == normalized,
                    BarcodeClaim.state == BarcodeState.VERIFIED_ACTIVE,
                    BarcodeClaim.active.is_(True),
                )
            )
            state = BarcodeState.VERIFIED_ACTIVE
            conflict_group_id = None
            if trusted is not None and trusted.variant_id != variant.id:
                state = BarcodeState.CONFLICTED
                conflict_group_id = trusted.conflict_group_id or str(uuid.uuid4())
                trusted.conflict_group_id = conflict_group_id
            claim = BarcodeClaim(
                variant_id=variant.id,
                original_value=original,
                normalized_value=normalized,
                symbology=item.get("symbology"),
                state=state,
                source=item.get("source", submission.source),
                source_ref=item.get("source_ref"),
                provenance={
                    "submission_id": submission.public_id,
                    "evidence": item.get("evidence", {}),
                },
                conflict_group_id=conflict_group_id,
            )
            self.session.add(claim)

    def _approve_aliases(
        self, variant: Variant, alias_items: list[dict[str, Any]], submission: Submission
    ) -> None:
        for item in alias_items:
            text = str(item["text"])
            self.session.add(
                Alias(
                    display_text=text,
                    normalized_text=normalize_text(text),
                    variant_id=variant.id,
                    alias_kind=item.get("kind", "COMMON"),
                    language=item.get("language"),
                    state=AliasState.APPROVED,
                    source=item.get("source", submission.source),
                    provenance={"submission_id": submission.public_id},
                )
            )

    def _get_or_create_brand(self, name: str) -> Brand:
        normalized = normalize_text(name)
        brand = self.session.scalar(select(Brand).where(Brand.normalized_name == normalized))
        if brand is None:
            brand = Brand(canonical_name=name, normalized_name=normalized)
            self.session.add(brand)
            self.session.flush()
        return brand

    def _get_or_create_category(self, name: str) -> Category:
        normalized = normalize_text(name)
        category = self.session.scalar(
            select(Category).where(Category.parent_id.is_(None), Category.normalized_name == normalized)
        )
        if category is None:
            category = Category(canonical_name=name, normalized_name=normalized)
            self.session.add(category)
            self.session.flush()
        return category

    def _changes(self, submission: Submission) -> dict[str, Any]:
        return {change.field_path: change.proposed_value for change in submission.changes}

    def _update_new_coverage(self, submission: Submission, state: CoverageState) -> None:
        coverage = self.session.scalar(
            select(BusinessCoverage).where(BusinessCoverage.submission_id == submission.id)
        )
        if coverage is not None and coverage.variant_id is None:
            coverage.state = state

    def _link_new_coverage(self, submission: Submission, variant: Variant, *, trusted: bool) -> None:
        coverage = self.session.scalar(
            select(BusinessCoverage).where(BusinessCoverage.submission_id == submission.id)
        )
        if coverage is not None:
            coverage.variant_id = variant.id
            coverage.state = CoverageState.LINKED_APPROVED if trusted else CoverageState.SUBMITTED_PENDING
            coverage.first_linked_at = datetime.now(UTC)
            coverage.last_confirmed_at = datetime.now(UTC)

    def _is_published(self, variant_id: str) -> bool:
        return (
            self.session.scalar(
                select(PublicationEntry.id)
                .join(PublicationSnapshot)
                .where(
                    PublicationEntry.variant_id == variant_id,
                    PublicationSnapshot.state.in_(["PUBLISHED", "SUPERSEDED"]),
                )
                .limit(1)
            )
            is not None
        )

    @staticmethod
    def _dto(review: ReviewCase) -> ReviewDto:
        submission = review.submission
        return ReviewDto(
            review_id=review.public_id,
            submission_id=submission.public_id,
            reason=review.reason,
            state=review.state.value,
            submission_state=submission.state.value,
            business_id=submission.business_id,
            business_product_ref=submission.business_product_ref,
            changes=[
                {
                    "field_path": change.field_path,
                    "old_value": change.old_value,
                    "proposed_value": change.proposed_value,
                    "evidence": change.evidence,
                }
                for change in submission.changes
            ],
        )
