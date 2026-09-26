from sqlalchemy.orm import Session

from ncpc_service.auth import Principal
from ncpc_service.publication import PublicationService
from ncpc_service.review import ReviewService
from ncpc_service.schemas import (
    BarcodeInput,
    NewProductSubmissionRequest,
    ReviewDecisionRequest,
)
from ncpc_service.submissions import SubmissionService


def create_approved_product(
    session: Session,
    business: Principal,
    admin: Principal,
    *,
    business_product_ref: str,
    name: str,
    barcode: str,
) -> tuple[str, str, str]:
    result = SubmissionService(session).submit_product(
        NewProductSubmissionRequest(
            business_id=business.business_id or "",
            business_product_ref=f"shop-test:{business_product_ref}",
            shop_id="shop-test",
            idempotency_key=f"submit-{business_product_ref}",
            canonical_name=name,
            variant_name=f"{name} 500 ml",
            pack_definition={"primary_measure": {"value": 500, "unit": "ml"}},
            barcodes=[BarcodeInput(value=barcode, source="scanned")],
        ),
        business,
    )
    reviewed = ReviewService(session).decide(
        result.review_id or "",
        ReviewDecisionRequest(outcome="APPROVE_NEW", rationale="Evidence verified"),
        admin,
    )
    session.commit()
    return reviewed.submission_id, reviewed.ncpc_product_id or "", reviewed.ncpc_variant_id or ""


def publish(session: Session, admin: Principal, version: str):
    result = PublicationService(session).publish(admin, requested_version=version)
    session.commit()
    return result
