from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .audit import record_audit
from .auth import Principal
from .database import next_public_id
from .enums import (
    CoverageState,
    LifecycleState,
    RelationshipType,
    ReviewOutcome,
    ReviewState,
    SubmissionState,
    SubmissionType,
)
from .errors import ConflictError, NotFoundError
from .models import (
    BusinessCoverage,
    IdentityRelationship,
    ProposedChange,
    PublicationEntry,
    PublicationSnapshot,
    ReviewCase,
    ReviewDecision,
    Submission,
    Variant,
)
from .schemas import MergeResultDto, MergeVariantRequest


class MergeService:
    def __init__(self, session: Session):
        self.session = session

    def merge_variant(
        self,
        source_variant_id: str,
        request: MergeVariantRequest,
        principal: Principal,
        *,
        request_id: str | None = None,
    ) -> MergeResultDto:
        principal.require_scope("identities:merge")
        existing_submission = self.session.scalar(
            select(Submission).where(
                Submission.submitter_client_id == principal.client_id,
                Submission.idempotency_key == request.idempotency_key,
            )
        )
        if existing_submission is not None:
            if existing_submission.review_case is None or not existing_submission.review_case.decisions:
                raise ConflictError("idempotency key belongs to an incomplete operation")
            decision = existing_submission.review_case.decisions[-1]
            return MergeResultDto(**decision.decision_data["result"])

        source = self.session.scalar(
            select(Variant).where(Variant.public_id == source_variant_id).with_for_update()
        )
        survivor = self.session.scalar(
            select(Variant).where(Variant.public_id == request.surviving_variant_id).with_for_update()
        )
        if source is None or survivor is None:
            raise NotFoundError("source or surviving variant not found")
        if source.id == survivor.id:
            raise ConflictError("a variant cannot merge into itself")
        if source.lifecycle == LifecycleState.MERGED:
            raise ConflictError("source variant is already merged")
        if survivor.lifecycle != LifecycleState.ACTIVE:
            raise ConflictError("surviving variant must be active")

        submission = Submission(
            public_id=next_public_id(self.session, "SUB"),
            submission_type=SubmissionType.MERGE_IDENTITY,
            state=SubmissionState.APPROVED,
            target_product_id=source.product_id,
            target_variant_id=source.id,
            source="ncpc_admin",
            submitter_client_id=principal.client_id,
            idempotency_key=request.idempotency_key,
            decided_at=datetime.now(UTC),
        )
        self.session.add(submission)
        self.session.flush()
        self.session.add(
            ProposedChange(
                submission_id=submission.id,
                field_path="identity.merged_into",
                old_value=source.public_id,
                proposed_value=survivor.public_id,
                evidence={},
            )
        )
        review = ReviewCase(
            public_id=next_public_id(self.session, "REV"),
            submission_id=submission.id,
            reason="IDENTITY_MERGE",
            state=ReviewState.DECIDED,
            assigned_to=principal.client_id,
        )
        self.session.add(review)
        self.session.flush()

        source.lifecycle = LifecycleState.MERGED
        source.superseded_by_id = survivor.id
        source.version += 1
        remapped = self.session.scalars(
            select(BusinessCoverage).where(
                BusinessCoverage.variant_id == source.id,
                BusinessCoverage.active.is_(True),
            )
        ).all()
        survivor_published = self._is_currently_published(survivor.id)
        for coverage in remapped:
            coverage.variant_id = survivor.id
            coverage.state = CoverageState.LINKED_APPROVED if survivor_published else CoverageState.REMAPPED
        result = MergeResultDto(
            source_variant_id=source.public_id,
            surviving_variant_id=survivor.public_id,
            relationship=RelationshipType.MERGED_INTO.value,
            remapped_coverage_count=len(remapped),
        )
        decision = ReviewDecision(
            review_case_id=review.id,
            reviewer_client_id=principal.client_id,
            outcome=ReviewOutcome.APPROVE_CORRECTION,
            rationale=request.rationale,
            evidence={},
            decision_data={"operation": "MERGE_VARIANT", "result": result.model_dump(mode="json")},
        )
        self.session.add(decision)
        self.session.flush()
        self.session.add(
            IdentityRelationship(
                entity_kind="VARIANT",
                source_variant_id=source.id,
                target_variant_id=survivor.id,
                relationship_type=RelationshipType.MERGED_INTO,
                decision_id=decision.id,
            )
        )
        record_audit(
            self.session,
            event_type="VARIANT_MERGED",
            entity_kind="VARIANT",
            entity_id=source.public_id,
            actor_client_id=principal.client_id,
            request_id=request_id,
            old_value={"lifecycle": LifecycleState.ACTIVE.value},
            new_value={"lifecycle": LifecycleState.MERGED.value, "survivor": survivor.public_id},
            rationale=request.rationale,
        )
        self.session.flush()
        return result

    def _is_currently_published(self, variant_id: str) -> bool:
        return (
            self.session.scalar(
                select(PublicationEntry.id)
                .join(PublicationSnapshot)
                .where(
                    PublicationEntry.variant_id == variant_id,
                    PublicationSnapshot.state == "PUBLISHED",
                )
                .limit(1)
            )
            is not None
        )
