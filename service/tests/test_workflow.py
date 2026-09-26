from sqlalchemy import select
from sqlalchemy.orm import Session

from ncpc_service.catalogue import CatalogueService
from ncpc_service.enums import BarcodeState, CoverageState, VisibilityScope
from ncpc_service.errors import AuthorizationError
from ncpc_service.models import BarcodeClaim, BusinessCoverage
from ncpc_service.review import ReviewService
from ncpc_service.schemas import (
    BarcodeInput,
    CorrectionSubmissionRequest,
    ExistingVariantCoverageLinkRequest,
    NewProductSubmissionRequest,
    ReviewDecisionRequest,
)
from ncpc_service.submissions import SubmissionService
from ncpc_service.visibility import VisibilityService

from .helpers import create_approved_product, publish


def test_submission_review_publication_and_visibility(session: Session, principals):
    business = principals["business_a"]
    admin = principals["admin"]
    request = NewProductSubmissionRequest(
        business_id="business-a",
        business_product_ref="shop-1:TFP-001",
        shop_id="shop-1",
        idempotency_key="request-product-001",
        canonical_name="Coca-Cola Original",
        variant_name="Coca-Cola Original 500 ml Bottle",
        brand="Coca-Cola",
        category="Drinks",
        pack_definition={"primary_measure": {"value": 500, "unit": "ml"}, "packaging": "bottle"},
        barcodes=[BarcodeInput(value="0123456789012", source="scanned")],
    )
    first = SubmissionService(session).submit_product(request, business)
    second = SubmissionService(session).submit_product(request, business)
    assert first.submission_id == second.submission_id
    pending = VisibilityService(session).get("business-a", "shop-1:TFP-001", business)
    assert pending.effective_visibility == VisibilityScope.WITHIN_BUSINESS_PROVISIONAL

    approved = ReviewService(session).decide(
        first.review_id or "",
        ReviewDecisionRequest(outcome="APPROVE_NEW", rationale="Barcode and package verified"),
        admin,
    )
    session.commit()
    assert approved.ncpc_product_id.startswith("PRD-")
    assert approved.ncpc_variant_id.startswith("VAR-")
    assert (
        VisibilityService(session).get("business-a", "shop-1:TFP-001", business).effective_visibility
        == VisibilityScope.WITHIN_BUSINESS_PROVISIONAL
    )

    release = publish(session, admin, "NCPC-TEST-001")
    trusted = VisibilityService(session).get("business-a", "shop-1:TFP-001", business)
    assert trusted.effective_visibility == VisibilityScope.WIDER_TRUSTED
    assert trusted.release_version == release.version

    matches = CatalogueService(session).search_candidates(barcode="0123456789012")
    assert [match.ncpc_variant_id for match in matches] == [approved.ncpc_variant_id]
    public = matches[0].model_dump()
    assert not ({"price", "stock", "cost", "supplier", "batches", "availability"} & public.keys())


def test_tradeflow_can_link_existing_published_variant_with_shop_location(session: Session, principals):
    _, product_id, variant_id = create_approved_product(
        session,
        principals["business_a"],
        principals["admin"],
        business_product_ref="TFP-LINK-001",
        name="Linked Cola",
        barcode="0600000000001",
    )
    publish(session, principals["admin"], "NCPC-LINK-001")
    request = ExistingVariantCoverageLinkRequest(
        business_product_ref="shop-1:TFP-LINK-001",
        shop_id="shop-1",
        idempotency_key="tradeflow-link-001",
        ncpc_product_id=product_id,
        ncpc_variant_id=variant_id,
        location_projection={"country_id": "ZM", "province_name": "Lusaka"},
        exposure_preference="WITHIN_BUSINESS",
    )
    first = SubmissionService(session).link_existing_variant(
        "business-a", request, principals["business_a"]
    )
    second = SubmissionService(session).link_existing_variant(
        "business-a", request, principals["business_a"]
    )
    assert first == second
    assert first.state == CoverageState.LINKED_APPROVED
    assert first.shop_id == "shop-1"
    assert first.location_projection["province_name"] == "Lusaka"
    assert session.query(BusinessCoverage).count() == 2
    assert (
        session.query(BusinessCoverage)
        .filter_by(business_id="business-a", business_product_ref="shop-1:TFP-LINK-001")
        .count()
        == 1
    )


def test_correction_is_reviewed_and_snapshot_changes_only_after_publish(session: Session, principals):
    business = principals["business_a"]
    admin = principals["admin"]
    _, product_id, variant_id = create_approved_product(
        session,
        business,
        admin,
        business_product_ref="TFP-002",
        name="Coca Cola",
        barcode="0001234567890",
    )
    first_release = publish(session, admin, "NCPC-TEST-002")
    correction = SubmissionService(session).submit_correction(
        CorrectionSubmissionRequest(
            business_id="business-a",
            business_product_ref="shop-test:TFP-002",
            idempotency_key="correction-product-002",
            ncpc_product_id=product_id,
            ncpc_variant_id=variant_id,
            changes={"product.canonical_name": "Coca-Cola"},
        ),
        business,
    )
    ReviewService(session).decide(
        correction.review_id or "",
        ReviewDecisionRequest(outcome="APPROVE_CORRECTION", rationale="Spelling verified"),
        admin,
    )
    session.commit()
    assert CatalogueService(session).get_variant(variant_id).canonical_name == "Coca Cola"
    second_release = publish(session, admin, "NCPC-TEST-003")
    assert second_release.content_hash != first_release.content_hash
    assert CatalogueService(session).get_variant(variant_id).canonical_name == "Coca-Cola"


def test_business_correction_requires_a_shop_qualified_reference(session: Session, principals):
    with __import__("pytest").raises(AuthorizationError):
        SubmissionService(session).submit_correction(
            CorrectionSubmissionRequest(
                business_id="business-a",
                business_product_ref="TFP-UNQUALIFIED",
                idempotency_key="correction-unqualified-reference",
                ncpc_variant_id="VAR-000001",
                changes={"product.canonical_name": "Rejected before lookup"},
            ),
            principals["business_a"],
        )


def test_barcode_collision_preserves_existing_trusted_claim(session: Session, principals):
    business = principals["business_a"]
    admin = principals["admin"]
    create_approved_product(
        session,
        business,
        admin,
        business_product_ref="TFP-003",
        name="Product A",
        barcode="0600123456789",
    )
    create_approved_product(
        session,
        business,
        admin,
        business_product_ref="TFP-004",
        name="Product B",
        barcode="0600123456789",
    )
    claims = session.scalars(
        select(BarcodeClaim).where(BarcodeClaim.normalized_value == "0600123456789")
    ).all()
    assert sum(claim.state == BarcodeState.VERIFIED_ACTIVE for claim in claims) == 1
    assert sum(claim.state == BarcodeState.CONFLICTED for claim in claims) == 1
    assert all(claim.original_value.startswith("0") for claim in claims)


def test_rejected_new_product_is_hidden_but_coverage_survives(session: Session, principals):
    business = principals["business_a"]
    result = SubmissionService(session).submit_product(
        NewProductSubmissionRequest(
            business_id="business-a",
            business_product_ref="shop-1:TFP-005",
            shop_id="shop-1",
            idempotency_key="rejected-product-005",
            canonical_name="Unverified item",
        ),
        business,
    )
    ReviewService(session).decide(
        result.review_id or "",
        ReviewDecisionRequest(outcome="REJECT", rationale="Insufficient identity evidence"),
        principals["admin"],
    )
    session.commit()
    visibility = VisibilityService(session).get("business-a", "shop-1:TFP-005", business)
    assert visibility.effective_visibility == VisibilityScope.HIDDEN
    coverage = session.scalar(
        select(BusinessCoverage).where(BusinessCoverage.business_product_ref == "shop-1:TFP-005")
    )
    assert coverage is not None and coverage.state == CoverageState.REJECTED


def test_tenant_isolation_on_status_and_visibility(session: Session, principals):
    result = SubmissionService(session).submit_product(
        NewProductSubmissionRequest(
            business_id="business-a",
            business_product_ref="shop-1:TFP-006",
            shop_id="shop-1",
            idempotency_key="tenant-test-006",
            canonical_name="Tenant A item",
        ),
        principals["business_a"],
    )
    with __import__("pytest").raises(AuthorizationError):
        SubmissionService(session).get_status(result.submission_id, principals["business_b"])
    with __import__("pytest").raises(AuthorizationError):
        VisibilityService(session).get("business-a", "shop-1:TFP-006", principals["business_b"])


def test_wider_discovery_returns_only_published_opted_in_coverage(session: Session, principals):
    _, _, variant_id = create_approved_product(
        session,
        principals["business_a"],
        principals["admin"],
        business_product_ref="TFP-DISCOVERY",
        name="Discovery Cola",
        barcode="0888888888888",
    )
    assert VisibilityService(session).discover_by_variants([variant_id], principals["ntheemba"]) == []
    publish(session, principals["admin"], "NCPC-DISCOVERY-001")
    result = VisibilityService(session).discover_by_variants([variant_id], principals["ntheemba"])
    assert len(result) == 1
    assert result[0].business_product_ref == "shop-test:TFP-DISCOVERY"
    assert result[0].visibility == VisibilityScope.WIDER_TRUSTED
    with __import__("pytest").raises(AuthorizationError):
        VisibilityService(session).discover_by_variants([variant_id], principals["business_a"])
