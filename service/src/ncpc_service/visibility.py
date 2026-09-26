from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from .audit import record_audit
from .auth import Principal
from .enums import (
    CoverageState,
    ExposurePreference,
    PrincipalRole,
    SnapshotState,
    VisibilityScope,
)
from .errors import AuthorizationError, NotFoundError
from .models import BusinessCoverage, PublicationEntry, PublicationSnapshot, Variant
from .schemas import DiscoveryCoverageDto, VisibilityDto


class VisibilityService:
    def __init__(self, session: Session):
        self.session = session

    def get(self, business_id: str, business_product_ref: str, principal: Principal) -> VisibilityDto:
        principal.require_scope("coverage:read")
        principal.require_business(business_id)
        coverage = self.session.scalar(
            select(BusinessCoverage).where(
                BusinessCoverage.business_id == business_id,
                BusinessCoverage.business_product_ref == business_product_ref,
                BusinessCoverage.active.is_(True),
            )
        )
        if coverage is None:
            return VisibilityDto(
                business_id=business_id,
                business_product_ref=business_product_ref,
                coverage_state=None,
                business_preference=ExposurePreference.HIDDEN.value,
                trust_ceiling=VisibilityScope.HIDDEN,
                effective_visibility=VisibilityScope.HIDDEN,
                provisional=False,
                trusted=False,
                ncpc_variant_id=None,
                release_version=None,
            )
        published, release_version = self._current_publication(coverage.variant_id)
        ceiling = self._trust_ceiling(coverage.state, published)
        effective = self._apply_preference(ceiling, coverage.exposure_preference)
        variant = self.session.get(Variant, coverage.variant_id) if coverage.variant_id else None
        return VisibilityDto(
            business_id=business_id,
            business_product_ref=business_product_ref,
            coverage_state=coverage.state.value,
            business_preference=coverage.exposure_preference.value,
            trust_ceiling=ceiling,
            effective_visibility=effective,
            provisional=effective == VisibilityScope.WITHIN_BUSINESS_PROVISIONAL,
            trusted=effective in (VisibilityScope.WITHIN_BUSINESS_TRUSTED, VisibilityScope.WIDER_TRUSTED),
            ncpc_variant_id=variant.public_id if variant else None,
            release_version=release_version,
        )

    def set_preference(
        self,
        business_id: str,
        business_product_ref: str,
        preference: ExposurePreference,
        principal: Principal,
        *,
        request_id: str | None = None,
    ) -> VisibilityDto:
        principal.require_scope("coverage:write")
        principal.require_business(business_id)
        coverage = self.session.scalar(
            select(BusinessCoverage).where(
                BusinessCoverage.business_id == business_id,
                BusinessCoverage.business_product_ref == business_product_ref,
                BusinessCoverage.active.is_(True),
            )
        )
        if coverage is None:
            raise NotFoundError("coverage not found")
        old = coverage.exposure_preference
        coverage.exposure_preference = preference
        record_audit(
            self.session,
            event_type="COVERAGE_PREFERENCE_CHANGED",
            entity_kind="BUSINESS_COVERAGE",
            entity_id=coverage.id,
            actor_client_id=principal.client_id,
            request_id=request_id,
            old_value={"preference": old.value},
            new_value={"preference": preference.value},
        )
        self.session.flush()
        return self.get(business_id, business_product_ref, principal)

    def discover_by_variants(
        self, ncpc_variant_ids: list[str], principal: Principal
    ) -> list[DiscoveryCoverageDto]:
        principal.require_scope("discovery:read")
        if principal.role not in (PrincipalRole.NTHEEMBA, PrincipalRole.ADMIN):
            raise AuthorizationError("wider discovery requires an Ntheemba service principal")
        snapshot = self.session.scalar(
            select(PublicationSnapshot)
            .where(PublicationSnapshot.state == SnapshotState.PUBLISHED)
            .order_by(desc(PublicationSnapshot.published_at))
            .limit(1)
        )
        if snapshot is None:
            return []
        variants = self.session.scalars(select(Variant).where(Variant.public_id.in_(ncpc_variant_ids))).all()
        by_internal_id = {variant.id: variant.public_id for variant in variants}
        if not by_internal_id:
            return []
        published_ids = set(
            self.session.scalars(
                select(PublicationEntry.variant_id).where(
                    PublicationEntry.snapshot_id == snapshot.id,
                    PublicationEntry.variant_id.in_(by_internal_id),
                )
            )
        )
        rows = self.session.scalars(
            select(BusinessCoverage).where(
                BusinessCoverage.variant_id.in_(published_ids),
                BusinessCoverage.state == CoverageState.LINKED_APPROVED,
                BusinessCoverage.exposure_preference == ExposurePreference.WIDER,
                BusinessCoverage.active.is_(True),
            )
        ).all()
        return [
            DiscoveryCoverageDto(
                business_id=row.business_id,
                business_product_ref=row.business_product_ref,
                shop_id=row.shop_id,
                ncpc_variant_id=by_internal_id[row.variant_id],
                visibility=VisibilityScope.WIDER_TRUSTED,
                location_projection=row.location_projection,
                release_version=snapshot.version,
            )
            for row in rows
            if row.variant_id in by_internal_id
        ]

    def _current_publication(self, variant_id: str | None) -> tuple[bool, str | None]:
        if not variant_id:
            return False, None
        snapshot = self.session.scalar(
            select(PublicationSnapshot)
            .where(PublicationSnapshot.state == SnapshotState.PUBLISHED)
            .order_by(desc(PublicationSnapshot.published_at))
            .limit(1)
        )
        if snapshot is None:
            return False, None
        entry = self.session.scalar(
            select(PublicationEntry.id).where(
                PublicationEntry.snapshot_id == snapshot.id,
                PublicationEntry.variant_id == variant_id,
            )
        )
        return entry is not None, snapshot.version if entry is not None else None

    @staticmethod
    def _trust_ceiling(state: CoverageState, published: bool) -> VisibilityScope:
        if state in (
            CoverageState.SUBMITTED_PENDING,
            CoverageState.NEEDS_MORE_INFORMATION,
            CoverageState.STALE,
            CoverageState.REMAPPED,
        ):
            return VisibilityScope.WITHIN_BUSINESS_PROVISIONAL
        if state == CoverageState.LINKED_APPROVED:
            return VisibilityScope.WIDER_TRUSTED if published else VisibilityScope.WITHIN_BUSINESS_PROVISIONAL
        return VisibilityScope.HIDDEN

    @staticmethod
    def _apply_preference(ceiling: VisibilityScope, preference: ExposurePreference) -> VisibilityScope:
        if preference == ExposurePreference.HIDDEN or ceiling == VisibilityScope.HIDDEN:
            return VisibilityScope.HIDDEN
        if ceiling == VisibilityScope.WITHIN_BUSINESS_PROVISIONAL:
            return ceiling
        if preference == ExposurePreference.WITHIN_BUSINESS:
            return VisibilityScope.WITHIN_BUSINESS_TRUSTED
        return VisibilityScope.WIDER_TRUSTED
