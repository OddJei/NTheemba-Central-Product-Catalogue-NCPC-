from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .audit import record_audit
from .auth import Principal
from .catalogue import CatalogueService
from .database import next_public_id
from .enums import CoverageState, PrincipalRole, SubmissionState, SubmissionType
from .errors import AuthorizationError, ConflictError, NotFoundError
from .models import BusinessCoverage, Product, ProposedChange, ReviewCase, Submission, Variant
from .schemas import (
    CorrectionSubmissionRequest,
    ExistingVariantCoverageLinkRequest,
    NewProductSubmissionRequest,
    SubmissionStatusDto,
)


def _is_shop_qualified_product_ref(value: str) -> bool:
    shop_id, separator, product_ref = value.partition(":")
    return bool(shop_id and separator and product_ref)


class SubmissionService:
    def __init__(self, session: Session):
        self.session = session

    def link_existing_variant(
        self,
        business_id: str,
        request: ExistingVariantCoverageLinkRequest,
        principal: Principal,
        *,
        request_id: str | None = None,
    ):
        principal.require_scope("coverage:write")
        principal.require_business(business_id)
        if principal.role == PrincipalRole.BUSINESS and not request.business_product_ref.startswith(
            f"{request.shop_id}:"
        ):
            raise AuthorizationError(
                "business product reference must be qualified by the submitted shop ID"
            )

        verified = CatalogueService(self.session).verify_variant(
            ncpc_product_id=request.ncpc_product_id,
            ncpc_variant_id=request.ncpc_variant_id,
        )
        variant = self.session.scalar(
            select(Variant).where(Variant.public_id == request.ncpc_variant_id)
        )
        if variant is None:
            raise NotFoundError("published variant not found")

        existing = self.session.scalar(
            select(BusinessCoverage).where(
                BusinessCoverage.business_id == business_id,
                BusinessCoverage.business_product_ref == request.business_product_ref,
                BusinessCoverage.active.is_(True),
            )
        )
        if existing is not None:
            if existing.variant_id != variant.id or existing.shop_id != request.shop_id:
                raise ConflictError("an active coverage record already exists for this business product")
            return self._coverage_link_dto(existing, verified)

        coverage = BusinessCoverage(
            business_id=business_id,
            business_product_ref=request.business_product_ref,
            shop_id=request.shop_id,
            idempotency_key=request.idempotency_key,
            variant_id=variant.id,
            state=CoverageState.LINKED_APPROVED,
            exposure_preference=request.exposure_preference,
            source=request.source,
            location_projection=request.location_projection,
            first_linked_at=datetime.now(UTC),
            last_confirmed_at=datetime.now(UTC),
        )
        self.session.add(coverage)
        self.session.flush()
        record_audit(
            self.session,
            event_type="BUSINESS_COVERAGE_LINKED",
            entity_kind="BUSINESS_COVERAGE",
            entity_id=coverage.id,
            actor_client_id=principal.client_id,
            request_id=request_id,
            new_value={
                "business_id": business_id,
                "business_product_ref": request.business_product_ref,
                "shop_id": request.shop_id,
                "ncpc_product_id": request.ncpc_product_id,
                "ncpc_variant_id": request.ncpc_variant_id,
            },
        )
        return self._coverage_link_dto(coverage, verified)

    @staticmethod
    def _coverage_link_dto(coverage: BusinessCoverage, verified):
        from .schemas import CoverageLinkDto

        return CoverageLinkDto(
            business_id=coverage.business_id,
            business_product_ref=coverage.business_product_ref,
            shop_id=coverage.shop_id or "",
            state=coverage.state.value,
            ncpc_product_id=verified.ncpc_product_id,
            ncpc_variant_id=verified.ncpc_variant_id,
            exposure_preference=coverage.exposure_preference,
            location_projection=coverage.location_projection or {},
        )

    def _idempotent_existing(self, principal: Principal, key: str) -> Submission | None:
        return self.session.scalar(
            select(Submission).where(
                Submission.submitter_client_id == principal.client_id,
                Submission.idempotency_key == key,
            )
        )

    def submit_product(
        self,
        request: NewProductSubmissionRequest,
        principal: Principal,
        *,
        request_id: str | None = None,
    ) -> SubmissionStatusDto:
        principal.require_scope("submissions:write")
        principal.require_business(request.business_id)
        if principal.role == PrincipalRole.BUSINESS:
            if not request.shop_id:
                raise AuthorizationError("business product submissions must include a shop ID")
            if not (
                _is_shop_qualified_product_ref(request.business_product_ref)
                and request.business_product_ref.startswith(f"{request.shop_id}:")
            ):
                raise AuthorizationError(
                    "business product reference must be qualified by the submitted shop ID"
                )
        existing = self._idempotent_existing(principal, request.idempotency_key)
        if existing is not None:
            return self.status(existing, principal)

        active_coverage = self.session.scalar(
            select(BusinessCoverage).where(
                BusinessCoverage.business_id == request.business_id,
                BusinessCoverage.business_product_ref == request.business_product_ref,
                BusinessCoverage.active.is_(True),
            )
        )
        if active_coverage is not None:
            raise ConflictError("an active coverage record already exists for this business product")

        submission = Submission(
            public_id=next_public_id(self.session, "SUB"),
            submission_type=SubmissionType.NEW_PRODUCT,
            state=SubmissionState.PENDING_REVIEW,
            business_id=request.business_id,
            business_product_ref=request.business_product_ref,
            source=request.source,
            submitter_client_id=principal.client_id,
            idempotency_key=request.idempotency_key,
        )
        self.session.add(submission)
        self.session.flush()

        proposed = {
            "product.canonical_name": request.canonical_name,
            "variant.canonical_name": request.variant_name or request.canonical_name,
            "product.brand": request.brand,
            "product.category": request.category,
            "variant.pack_definition": request.pack_definition,
            "variant.attributes": request.attributes,
            "variant.barcodes": [item.model_dump(mode="json") for item in request.barcodes],
            "variant.aliases": [item.model_dump(mode="json") for item in request.aliases],
        }
        for field_path, proposed_value in proposed.items():
            if proposed_value in (None, [], {}):
                continue
            self.session.add(
                ProposedChange(
                    submission_id=submission.id,
                    field_path=field_path,
                    old_value=None,
                    proposed_value=proposed_value,
                    evidence={"source": request.source},
                )
            )

        review = ReviewCase(
            public_id=next_public_id(self.session, "REV"),
            submission_id=submission.id,
            reason="NEW_PRODUCT_IDENTITY",
        )
        self.session.add(review)
        coverage = BusinessCoverage(
            business_id=request.business_id,
            business_product_ref=request.business_product_ref,
            shop_id=request.shop_id,
            submission_id=submission.id,
            state=CoverageState.SUBMITTED_PENDING,
            exposure_preference=request.exposure_preference,
            source=request.source,
            location_projection=request.location_projection,
        )
        self.session.add(coverage)
        record_audit(
            self.session,
            event_type="SUBMISSION_CREATED",
            entity_kind="SUBMISSION",
            entity_id=submission.public_id,
            actor_client_id=principal.client_id,
            request_id=request_id,
            new_value={
                "state": submission.state.value,
                "business_id": request.business_id,
                "business_product_ref": request.business_product_ref,
            },
        )
        self.session.flush()
        return self.status(submission, principal)

    def submit_correction(
        self,
        request: CorrectionSubmissionRequest,
        principal: Principal,
        *,
        request_id: str | None = None,
    ) -> SubmissionStatusDto:
        principal.require_scope("submissions:write")
        principal.require_business(request.business_id)
        if principal.role == PrincipalRole.BUSINESS and not _is_shop_qualified_product_ref(
            request.business_product_ref
        ):
            raise AuthorizationError(
                "business correction reference must be qualified by a shop ID"
            )
        existing = self._idempotent_existing(principal, request.idempotency_key)
        if existing is not None:
            return self.status(existing, principal)

        variant = self.session.scalar(select(Variant).where(Variant.public_id == request.ncpc_variant_id))
        if variant is None:
            raise NotFoundError("target variant not found")
        product = self.session.get(Product, variant.product_id)
        if request.ncpc_product_id and product and product.public_id != request.ncpc_product_id:
            raise NotFoundError("target product/variant pair not found")

        submission = Submission(
            public_id=next_public_id(self.session, "SUB"),
            submission_type=SubmissionType.CORRECT_IDENTITY,
            state=SubmissionState.PENDING_REVIEW,
            business_id=request.business_id,
            business_product_ref=request.business_product_ref,
            target_product_id=product.id if product else None,
            target_variant_id=variant.id,
            source=request.source,
            submitter_client_id=principal.client_id,
            idempotency_key=request.idempotency_key,
        )
        self.session.add(submission)
        self.session.flush()
        for field_path, proposed_value in request.changes.items():
            self.session.add(
                ProposedChange(
                    submission_id=submission.id,
                    field_path=field_path,
                    old_value=self._current_value(product, variant, field_path),
                    proposed_value=proposed_value,
                    evidence=request.evidence,
                )
            )
        review = ReviewCase(
            public_id=next_public_id(self.session, "REV"),
            submission_id=submission.id,
            reason="IDENTITY_CORRECTION",
        )
        self.session.add(review)
        record_audit(
            self.session,
            event_type="CORRECTION_SUBMITTED",
            entity_kind="SUBMISSION",
            entity_id=submission.public_id,
            actor_client_id=principal.client_id,
            request_id=request_id,
            new_value={"state": submission.state.value, "target_variant": variant.public_id},
        )
        self.session.flush()
        return self.status(submission, principal)

    @staticmethod
    def _current_value(product: Product | None, variant: Variant, field_path: str) -> Any:
        values = {
            "product.canonical_name": product.canonical_name if product else None,
            "variant.canonical_name": variant.canonical_name,
            "variant.pack_definition": variant.pack_definition,
            "variant.attributes": variant.attributes,
        }
        return values.get(field_path)

    def get_status(self, public_id: str, principal: Principal) -> SubmissionStatusDto:
        principal.require_scope("submissions:read")
        submission = self.session.scalar(select(Submission).where(Submission.public_id == public_id))
        if submission is None:
            raise NotFoundError("submission not found")
        return self.status(submission, principal)

    def status(self, submission: Submission, principal: Principal) -> SubmissionStatusDto:
        if (
            principal.business_id is not None
            and submission.business_id is not None
            and principal.business_id != submission.business_id
        ):
            raise AuthorizationError("business scope mismatch")
        product = (
            self.session.get(Product, submission.target_product_id) if submission.target_product_id else None
        )
        variant = (
            self.session.get(Variant, submission.target_variant_id) if submission.target_variant_id else None
        )
        return SubmissionStatusDto(
            submission_id=submission.public_id,
            state=submission.state.value,
            business_id=submission.business_id,
            business_product_ref=submission.business_product_ref,
            ncpc_product_id=product.public_id if product else None,
            ncpc_variant_id=variant.public_id if variant else None,
            review_id=submission.review_case.public_id if submission.review_case else None,
            submitted_at=submission.submitted_at,
            decided_at=submission.decided_at,
            published_at=submission.published_at,
        )
